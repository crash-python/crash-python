# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Pattern, Union, List, Dict, Any, Optional, BinaryIO

import sys
import re
import fnmatch
import os.path
import tempfile

from elftools.elf.elffile import ELFFile
import gdb

# This is from the C extension and published via __all__; pylint bug?
# pylint: disable=no-name-in-module
from zstd import decompress as zstd_decompress

import crash
import crash.target
from crash.types.module import for_each_module, for_each_module_section
from crash.util import get_symbol_value
from crash.util.symbols import Types
from crash.exceptions import MissingSymbolError, InvalidArgumentError
from crash.infra.callback import pause_objfile_callbacks, unpause_objfile_callbacks
from crash.cache.syscache import utsname

class CrashKernelError(RuntimeError):
    """Raised when an error occurs while initializing the debugging session"""

class _NoMatchingFileError(FileNotFoundError):
    pass

class _ModinfoMismatchError(ValueError):
    _fmt = "module {} has mismatched {} (got `{}' expected `{}')"
    def __init__(self, attribute: str, path: str, value: Optional[str],
                 expected_value: Optional[str]) -> None:
        msg = self._fmt.format(path, attribute, value, expected_value)
        super().__init__(msg)
        self.path = path
        self.value = value
        self.expected_value = expected_value
        self.attribute = attribute

class _ModVersionMismatchError(_ModinfoMismatchError):
    def __init__(self, path: str, module_value: Optional[str],
                 expected_value: Optional[str]) -> None:
        super().__init__('vermagic', path, module_value, expected_value)

class _ModSourceVersionMismatchError(_ModinfoMismatchError):
    def __init__(self, path: str, module_value: Optional[str],
                 expected_value: Optional[str]) -> None:
        super().__init__('srcversion', path, module_value, expected_value)

LINUX_KERNEL_PID = 1

PathSpecifier = Union[List[str], str]

class CrashKernel:
    """
    Initialize a basic kernel semantic debugging session.

    This means that we load the following:

    - Kernel image symbol table (and debuginfo, if not integrated)
      relocated to the base offset used by kASLR
    - Kernel modules that were loaded on the the crashed system (again,
      with debuginfo if not integrated)
    - Percpu ranges used by kernel module
    - Architecture-specific details
    - Linux tasks populated into the GDB thread table

    If kernel module files and debuginfo cannot be located, backtraces
    may be incomplete if the addresses used by the modules are crossed.
    Percpu ranges will be properly loaded regardless.

    For arguments that accept paths to specify a base directory to be
    used, the entire directory structure will be read and cached to
    speed up subsequent searches.  Still, reading large directory trees
    is a time consuming operation and being exact as possible will
    improve startup time.

    Args:
        root (None for defaults): The roots of trees
            to search for debuginfo files.  When specified, all roots
            will be searched using the following arguments (including
            the absolute paths in the defaults if unspecified).

            Defaults to: /

        vmlinux_debuginfo (None for defaults): The
            location of the separate debuginfo file corresponding
            to the kernel being debugged.

            Defaults to:

            - <loaded kernel path>.debug
            - ./vmlinux-<kernel version>.debug
            - /usr/lib/debug/.build-id/xx/<build-id>.debug
            - /usr/lib/debug/<loaded kernel path>.debug
            - /usr/lib/debug/boot/<loaded kernel name>.debug
            - /usr/lib/debug/boot/vmlinux-<kernel version>


        module_path (None for defaults): The base directory to
            be used to search for kernel modules (e.g. module.ko) to be
            used to load symbols for the kernel being debugged.

            Defaults to:

            - ./modules
            - /lib/modules/<kernel-version>


        module_debuginfo_path (None for defaults): The base
            directory to search for debuginfo matching the kernel
            modules already loaded.

            Defaults to:

            - ./modules.debug
            - /usr/lib/debug/.build-id/xx/<build-id>.debug
            - /usr/lib/debug/lib/modules/<kernel-version>


    Raises:
        CrashKernelError: If the kernel debuginfo cannot be loaded.
        InvalidArgumentError: If any of the arguments are not None, str,
                   or list of str

    """
    types = Types(['char *'])

    # pylint: disable=unused-argument
    def __init__(self, roots: PathSpecifier = None,
                 vmlinux_debuginfo: PathSpecifier = None,
                 module_path: PathSpecifier = None,
                 module_debuginfo_path: PathSpecifier = None,
                 verbose: bool = False, debug: bool = False) -> None:

        self.target = crash.target.check_target()

        self.findmap: Dict[str, Dict[Any, Any]] = dict()
        self.modules_order: Dict[str, Dict[str, str]] = dict()
        obj = gdb.objfiles()[0]
        if not obj.filename:
            raise RuntimeError("loaded objfile has no filename???")
        kernel = os.path.basename(obj.filename)

        self.kernel = kernel
        self.version = self.extract_version()

        self._setup_roots(roots, verbose)
        self._setup_vmlinux_debuginfo(vmlinux_debuginfo, verbose)
        self._setup_module_path(module_path, verbose)
        self._setup_module_debuginfo_path(module_debuginfo_path, verbose)

        # We need separate debuginfo.  Let's go find it.
        path_list = []
        build_id_path = self.build_id_path(obj)
        if build_id_path:
            path_list.append(build_id_path)
        path_list += self.vmlinux_debuginfo
        if not obj.has_symbols():
            print("Loading debug symbols for vmlinux")
            for path in path_list:
                try:
                    obj.add_separate_debug_file(path)
                    if obj.has_symbols():
                        break
                except gdb.error:
                    pass

        if not obj.has_symbols():
            raise CrashKernelError("Couldn't locate debuginfo for {}"
                                   .format(kernel))

        self.vermagic = self.extract_vermagic()

    def _setup_roots(self, roots: PathSpecifier = None,
                     verbose: bool = False) -> None:
        if roots is None:
            self.roots = ["/"]
        elif isinstance(roots, list) and roots and isinstance(roots[0], str):
            x = None
            for root in roots:
                if os.path.exists(root):
                    if x is None:
                        x = [root]
                    else:
                        x.append(root)
                else:
                    print("root {} does not exist".format(root))

            if x is None:
                x = ["/"]
            self.roots = x
        elif isinstance(roots, str):
            x = None
            if os.path.exists(roots):
                if x is None:
                    x = [roots]
                else:
                    x.append(roots)
            if x is None:
                x = ["/"]
            self.roots = x
        else:
            raise InvalidArgumentError("roots must be None, str, or list of str")
        if verbose:
            print("roots={}".format(self.roots))

    def _find_debuginfo_paths(self, variants: List[str]) -> List[str]:
        x: List[str] = list()

        for root in self.roots:
            for debug_path in ["", "usr/lib/debug"]:
                for variant in variants:
                    path = os.path.join(root, debug_path, variant)
                    if os.path.exists(path):
                        x.append(path)

        return x

    def _setup_vmlinux_debuginfo(self, vmlinux_debuginfo: PathSpecifier = None,
                                 verbose: bool = False) -> None:
        if vmlinux_debuginfo is None:
            defaults = [
                "{}.debug".format(self.kernel),
                "vmlinux-{}.debug".format(self.version),
                "boot/{}.debug".format(os.path.basename(self.kernel)),
                "boot/vmlinux-{}.debug".format(self.version),
            ]

            self.vmlinux_debuginfo = self._find_debuginfo_paths(defaults)

        elif (isinstance(vmlinux_debuginfo, list) and vmlinux_debuginfo and
              isinstance(vmlinux_debuginfo[0], str)):
            self.vmlinux_debuginfo = vmlinux_debuginfo
        elif isinstance(vmlinux_debuginfo, str):
            self.vmlinux_debuginfo = [vmlinux_debuginfo]
        else:
            raise InvalidArgumentError("vmlinux_debuginfo must be None, str, or list of str")

        if verbose:
            print("vmlinux_debuginfo={}".format(self.vmlinux_debuginfo))

    def _setup_module_path(self, module_path: PathSpecifier = None,
                           verbose: bool = False) -> None:
        x: List[str] = []
        if module_path is None:

            path = "modules"
            if os.path.exists(path):
                x.append(path)

            for root in self.roots:
                path = "{}/lib/modules/{}".format(root, self.version)
                if os.path.exists(path):
                    x.append(path)

            self.module_path = x
        elif (isinstance(module_path, list) and
              isinstance(module_path[0], str)):
            for root in self.roots:
                for mpath in module_path:
                    path = "{}/{}".format(root, mpath)
                    if os.path.exists(path):
                        x.append(path)

            self.module_path = x
        elif isinstance(module_path, str):
            if os.path.exists(module_path):
                x.append(module_path)

            self.module_path = x
        else:
            raise InvalidArgumentError("module_path must be None, str, or list of str")

        if verbose:
            print("module_path={}".format(self.module_path))

    def _setup_module_debuginfo_path(self, module_debuginfo_path: PathSpecifier = None,
                                     verbose: bool = False) -> None:
        x: List[str] = []
        if module_debuginfo_path is None:
            defaults = [
                "modules.debug",
                "lib/modules/{}".format(self.version),
            ]

            self.module_debuginfo_path = self._find_debuginfo_paths(defaults)
        elif (isinstance(module_debuginfo_path, list) and
              isinstance(module_debuginfo_path[0], str)):

            for root in self.roots:
                for mpath in module_debuginfo_path:
                    path = "{}/{}".format(root, mpath)
                    if os.path.exists(path):
                        x.append(path)

            self.module_debuginfo_path = x
        elif isinstance(module_debuginfo_path, str):

            for root in self.roots:
                path = "{}/{}".format(root, module_debuginfo_path)
                if os.path.exists(path):
                    x.append(path)

            self.module_debuginfo_path = x
        else:
            raise InvalidArgumentError("module_debuginfo_path must be None, str, or list of str")

        if verbose:
            print("module_debuginfo_path={}".format(self.module_debuginfo_path))

    # When working without a symbol table, we still need to be able
    # to resolve version information.
    def _get_minsymbol_as_string(self, name: str) -> str:
        sym = gdb.lookup_minimal_symbol(name)
        if sym is None:
            raise MissingSymbolError(name)

        val = sym.value()

        return val.address.cast(self.types.char_p_type).string()

    def extract_version(self) -> str:
        """
        Returns the version from the loaded vmlinux

        If debuginfo is available, ``init_uts_ns`` will be used.
        Otherwise, it will be extracted from the version banner.

        Returns:
            str: The version text.
        """
        try:
            uts = get_symbol_value('init_uts_ns')
            return uts['name']['release'].string()
        except (AttributeError, NameError, MissingSymbolError):
            pass

        banner = self._get_minsymbol_as_string('linux_banner')

        return banner.split(' ')[2]

    def extract_vermagic(self) -> str:
        """
        Returns the vermagic from the loaded vmlinux

        Returns:
            str: The version text.
        """
        try:
            magic = get_symbol_value('vermagic')
            return magic.string()
        except (AttributeError, NameError):
            pass

        return self._get_minsymbol_as_string('vermagic')

    def extract_modinfo_from_module(self, modfile: BinaryIO) -> Dict[str, str]:
        """
        Returns the modinfo from a module file

        Args:
            modpath: An open module file

        Returns:
            dict: A dictionary containing the names and values of the modinfo
            variables.
        """

        elf = ELFFile(modfile)
        modinfo = elf.get_section_by_name('.modinfo')

        d = {}
        for line in modinfo.data().split(b'\x00'):
            val = line.decode('utf-8')
            if val:
                eq = val.index('=')
                d[val[0:eq]] = val[eq + 1:]

        del elf
        return d

    def _get_module_sections(self, module: gdb.Value) -> str:
        out = []
        for (name, addr) in for_each_module_section(module):
            out.append("-s {} {:#x}".format(name, addr))
        return " ".join(out)

    def _check_module_version(self, modfile: BinaryIO, module: gdb.Value) -> None:
        modinfo = self.extract_modinfo_from_module(modfile)
        modpath = modfile.name

        vermagic = modinfo.get('vermagic', None)

        if vermagic != self.vermagic:
            raise _ModVersionMismatchError(modpath, vermagic, self.vermagic)

        mi_srcversion = modinfo.get('srcversion', None)

        mod_srcversion = None
        if 'srcversion' in module.type:
            mod_srcversion = module['srcversion'].string()

        if mi_srcversion != mod_srcversion:
            raise _ModSourceVersionMismatchError(modpath, mi_srcversion,
                                                 mod_srcversion)

    def _try_load_module(self, modname: str, module: gdb.Value, modfile: BinaryIO,
                         verbose: bool = False, debug: bool = False) -> gdb.Objfile:
        self._check_module_version(modfile, module)

        modpath = modfile.name

        if 'module_core' in module.type:
            addr = int(module['module_core'])
        else:
            addr = int(module['core_layout']['base'])

        if debug:
            print(f"Loading {modpath} at {addr:#x} from {modname}")
        elif verbose:
            print(f"Loading {modname} at {addr:#x}")
        else:
            print(".", end='')
            sys.stdout.flush()

        sections = self._get_module_sections(module)

        percpu = int(module['percpu'])
        if percpu > 0:
            sections += " -s .data..percpu {:#x}".format(percpu)

        sections += " -o 0xff000000"

        try:
            result = gdb.execute("add-symbol-file {} {:#x} {}"
                                 .format(modpath, addr, sections),
                                 to_string=True)
        except gdb.error as e:
            raise CrashKernelError("Error while loading module `{}': {}"
                                   .format(modname, str(e))) from e
        if debug:
            print(result)

        return gdb.lookup_objfile(modpath)

    def try_load_module(self, modname: str, module: gdb.Value, modpath: str,
                        tmpdirname: str,
                        verbose: bool = False, debug: bool = False) -> gdb.Objfile:
        if modpath.endswith(".zst"):
            with open(modpath, 'rb') as cmodfile:
                with open(os.path.join(tmpdirname, modname + ".ko"), 'w+b') as modfile:
                    modfile.write(zstd_decompress(cmodfile.read()))
                    return self._try_load_module(modname, module, modfile, debug)
        else:
            with open(modpath, 'rb') as modfile:
                return self._try_load_module(modname, module, modfile, debug)


    def load_modules(self, verbose: bool = False, debug: bool = False) -> None:
        """
        Load modules (including debuginfo) into the crash session.

        This routine will attempt to locate modules and the corresponding
        debuginfo files, if separate, using the parameters defined
        when the CrashKernel object was initialized.

        Args:
            verbose (default=False): enable verbose output
            debug (default=False): enable even more verbose debugging output

        Raises:
            CrashKernelError: An error was encountered while loading a module.
                This does not include a failure to locate a module or
                its debuginfo.
        """
        count = 0
        for module in for_each_module():
            count += 1
        print(f"Loading {count} modules for {utsname.release}", end='')
        if verbose:
            print(":", flush=True)
        else:
            print(".", end='', flush=True)
        failed = 0
        loaded = 0

        pause_objfile_callbacks()
        with tempfile.TemporaryDirectory() as tmpdirname:
            for module in for_each_module():
                modname = module['name'].string()
                modfname = f"{modname}.ko"
                objfile = None
                for path in self.module_path:

                    try:
                        modpath = self._find_module_file(modfname, path)
                    except _NoMatchingFileError:
                        continue

                    try:
                        objfile = self.try_load_module(modname, module, modpath,
                                                       tmpdirname, verbose, debug)
                    except (_ModinfoMismatchError, OSError) as e:
                        if verbose:
                            print(f"Module open failed: {str(e)}")
                        continue

                    if not objfile.has_symbols():
                        self._load_module_debuginfo(objfile, modpath, verbose)
                    elif debug:
                        print(" + has debug symbols")
                    break

                if objfile:
                    if not objfile.has_symbols():
                        print("Couldn't find debuginfo for {}".format(modname))
                    loaded += 1
                else:
                    if failed == 0:
                        print()
                    print("Couldn't find module file for {}".format(modname))
                    failed += 1

                if (loaded + failed) % 10 == 10:
                    print(".", end='')
                    sys.stdout.flush()
        print(" done. ({} loaded".format(loaded), end='')
        if failed:
            print(", {} failed)".format(failed))
        else:
            print(")")

        # We shouldn't need this again, so why keep it around?
        del self.findmap
        self.findmap = {}
        unpause_objfile_callbacks()

    def _normalize_modname(self, mod: str) -> str:
        return mod.replace('-', '_')

    def _cache_modules_order(self, path: str) -> None:
        self.modules_order[path] = dict()
        order = os.path.join(path, "modules.order")
        try:
            f = open(order)
            for line in f.readlines():
                modpath = line.rstrip()
                modname = self._normalize_modname(os.path.basename(modpath))
                if modname[:7] == "kernel/":
                    modname = modname[7:]
                modpath = os.path.join(path, modpath)
                if os.path.exists(modpath):
                    self.modules_order[path][modname] = modpath
                if os.path.exists(modpath + ".zst"):
                    self.modules_order[path][modname] = modpath + ".zst"
            f.close()
        except OSError:
            pass

    def _get_module_path_from_modules_order(self, path: str, name: str) -> str:
        if not path in self.modules_order:
            self._cache_modules_order(path)

        try:
            return self.modules_order[path][name]
        except KeyError:
            raise _NoMatchingFileError(name) from None

    def _cache_file_tree(self, path: str, regex: Pattern[str] = None) -> None:
        if not path in self.findmap:
            self.findmap[path] = {
                'filters' : [],
                'files' : {},
            }

        # If we've walked this path with no filters, we have everything
        # already.
        if self.findmap[path]['filters'] is None:
            return

        if regex is None:
            self.findmap[path]['filters'] = None
        else:
            pattern = regex.pattern
            if pattern in self.findmap[path]['filters']:
                return
            self.findmap[path]['filters'].append(pattern)

        # pylint: disable=unused-variable
        for root, dirs, files in os.walk(path):
            for filename in files:
                modname = self._normalize_modname(filename)

                if regex and regex.match(modname) is None:
                    continue

                modpath = os.path.join(root, filename)
                self.findmap[path]['files'][modname] = modpath

    def _get_file_path_from_tree_search(self, path: str, name: str,
                                        regex: Pattern[str] = None) -> str:
        self._cache_file_tree(path, regex)

        try:
            modname = self._normalize_modname(name)
            return self.findmap[path]['files'][modname]
        except KeyError:
            raise _NoMatchingFileError(name) from None

    def _find_module_file(self, name: str, path: str) -> str:
        try:
            return self._get_module_path_from_modules_order(path, name)
        except _NoMatchingFileError:
            pass

        regex = re.compile(fnmatch.translate("*.ko"))
        return self._get_file_path_from_tree_search(path, name, regex)

    def _find_module_debuginfo_file(self, name: str, path: str) -> str:
        regex = re.compile(fnmatch.translate("*.ko.debug"))
        return self._get_file_path_from_tree_search(path, name, regex)

    @staticmethod
    def build_id_path(objfile: gdb.Objfile) -> Optional[str]:
        """
        Returns the relative path for debuginfo using the objfile's build-id.

        Args:
            objfile: The objfile for which to return the path
        """
        build_id = objfile.build_id
        if build_id is None:
            return None
        return ".build_id/{}/{}.debug".format(build_id[0:2], build_id[2:])

    def _try_load_debuginfo(self, objfile: gdb.Objfile,
                            path: str, verbose: bool = False) -> bool:
        if not os.path.exists(path):
            return False

        try:
            if verbose:
                print(" + Loading debuginfo: {}".format(path))
            objfile.add_separate_debug_file(path)
            if objfile.has_symbols():
                return True
        except gdb.error as e:
            print(e)

        return False

    def _load_module_debuginfo(self, objfile: gdb.Objfile,
                               modpath: str = None,
                               verbose: bool = False) -> None:
        if modpath is None:
            modpath = objfile.filename
        if modpath is None:
            raise RuntimeError("loaded objfile has no filename???")
        if ".gz" in modpath:
            modpath = modpath[:-3]
        elif ".zst" in modpath:
            modpath = modpath[:-4]
        filename = "{}.debug".format(os.path.basename(modpath))

        build_id_path = self.build_id_path(objfile)

        for path in self.module_debuginfo_path:
            if build_id_path:
                filepath = "{}/{}".format(path, build_id_path)
                if self._try_load_debuginfo(objfile, filepath, verbose):
                    break

            try:
                filepath = self._find_module_debuginfo_file(filename, path)
            except _NoMatchingFileError:
                continue

            if self._try_load_debuginfo(objfile, filepath, verbose):
                break
