# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Pattern, Union, List, Dict, Any, Optional

import sys
import re
import fnmatch
import os.path

from elftools.elf.elffile import ELFFile

import crash.arch
import crash.arch.x86_64
import crash.arch.ppc64
from crash.types.module import for_each_module, for_each_module_section
from crash.util import get_symbol_value
from crash.util.symbols import Types, Symvals, Symbols
from crash.exceptions import MissingSymbolError, InvalidArgumentError

import gdb

class CrashKernelError(RuntimeError):
    pass

class NoMatchingFileError(FileNotFoundError):
    pass

class ModinfoMismatchError(ValueError):
    _fmt = "module {} has mismatched {} (got `{}' expected `{}')"
    def __init__(self, attribute: str, path: str, value: Optional[str],
                 expected_value: Optional[str]) -> None:
        msg = self._fmt.format(path, attribute, value, expected_value)
        super().__init__(msg)
        self.path = path
        self.value = value
        self.expected_value = expected_value
        self.attribute = attribute

class ModVersionMismatchError(ModinfoMismatchError):
    def __init__(self, path: str, module_value: Optional[str],
                 expected_value: Optional[str]) -> None:
        super().__init__('vermagic', path, module_value, expected_value)

class ModSourceVersionMismatchError(ModinfoMismatchError):
    def __init__(self, path: str, module_value: Optional[str],
                 expected_value: Optional[str]) -> None:
        super().__init__('srcversion', path, module_value, expected_value)

LINUX_KERNEL_PID = 1

PathSpecifier = Union[List[str], str]

class CrashKernel(object):
    types = Types(['char *'])
    symvals = Symvals(['init_task'])
    symbols = Symbols(['runqueues'])

    # pylint: disable=unused-argument
    def __init__(self, roots: PathSpecifier = None,
                 vmlinux_debuginfo: PathSpecifier = None,
                 module_path: PathSpecifier = None,
                 module_debuginfo_path: PathSpecifier = None,
                 verbose: bool = False, debug: bool = False) -> None:
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
            root (str or list of str, None for defaults): The roots of trees
                to search for debuginfo files.  When specified, all roots
                will be searched using the following arguments (including
                the absolute paths in the defaults if unspecified).

                Defaults to: /

            vmlinux_debuginfo (str or list of str, None for defaults): The
                location of the separate debuginfo file corresponding
                to the kernel being debugged.

                Defaults to:
                - <loaded kernel path>.debug
                - ./vmlinux-<kernel version>.debug
                - /usr/lib/debug/.build-id/xx/<build-id>.debug
                - /usr/lib/debug/<loaded kernel path>.debug
                - /usr/lib/debug/boot/<loaded kernel name>.debug
                - /usr/lib/debug/boot/vmlinux-<kernel version>

            module_path (string, None for defaults): The base directory to
                be used to search for kernel modules (e.g. module.ko) to be
                used to load symbols for the kernel being debugged.

                Defaults to:
                - ./modules
                - /lib/modules/<kernel-version>

            module_debuginfo_path (string, None for defaults): The base
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
        self.findmap: Dict[str, Dict[Any, Any]] = dict()
        self.modules_order: Dict[str, Dict[str, str]] = dict()
        obj = gdb.objfiles()[0]
        kernel = os.path.basename(obj.filename)

        self.kernel = kernel
        self.version = self.extract_version()

        self._setup_roots(roots, verbose)
        self._setup_vmlinux_debuginfo(vmlinux_debuginfo)
        self._setup_module_path(module_path, verbose)
        self._setup_module_debuginfo_path(module_debuginfo_path, verbose)

        # We need separate debuginfo.  Let's go find it.
        if not obj.has_symbols():
            print("Loading debug symbols for vmlinux")
            for path in [self.build_id_path(obj)] + self.vmlinux_debuginfo:
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

        archname = obj.architecture.name()
        try:
            archclass = crash.arch.get_architecture(archname)
        except RuntimeError as e:
            raise CrashKernelError(str(e))

        self.arch = archclass()

        self.target = gdb.current_target()
        self.vmcore = self.target.kdump

        self.target.fetch_registers = self.fetch_registers
        self.crashing_thread = None

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

    def _setup_vmlinux_debuginfo(self, vmlinux_debuginfo: PathSpecifier = None,
                                 verbose: bool = False) -> None:
        debugroot = "/usr/lib/debug"
        if vmlinux_debuginfo is None:
            x: List[str] = []
            defaults = [
                "{}.debug".format(self.kernel),
                "vmlinux-{}.debug".format(self.version),
                "{}/{}.debug".format(debugroot, self.kernel),
                "{}/boot/{}.debug".format(debugroot,
                                          os.path.basename(self.kernel)),
                "{}/boot/vmlinux-{}.debug".format(debugroot, self.version),
            ]
            for root in self.roots:
                for mpath in defaults:
                    path = "{}/{}".format(root, mpath)
                    if os.path.exists(path):
                        if x is None:
                            x = [path]
                        else:
                            x.append(path)

            self.vmlinux_debuginfo = x

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
        debugroot = "/usr/lib/debug"

        x: List[str] = []
        if module_debuginfo_path is None:

            path = "modules.debug"
            if os.path.exists(path):
                x.append(path)

            for root in self.roots:
                path = "{}/{}/lib/modules/{}".format(root, debugroot,
                                                     self.version)
                if os.path.exists(path):
                    x.append(path)
            self.module_debuginfo_path = x
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
        sym = gdb.lookup_minimal_symbol(name).value()

        return sym.address.cast(self.types.char_p_type).string()

    def extract_version(self) -> str:
        try:
            uts = get_symbol_value('init_uts_ns')
            return uts['name']['release'].string()
        except (AttributeError, NameError, MissingSymbolError):
            pass

        banner = self._get_minsymbol_as_string('linux_banner')

        return banner.split(' ')[2]

    def extract_vermagic(self) -> str:
        try:
            magic = get_symbol_value('vermagic')
            return magic.string()
        except (AttributeError, NameError):
            pass

        return self._get_minsymbol_as_string('vermagic')

    def extract_modinfo_from_module(self, modpath: str) -> Dict[str, str]:
        f = open(modpath, 'rb')

        elf = ELFFile(f)
        modinfo = elf.get_section_by_name('.modinfo')

        d = {}
        for line in modinfo.data().split(b'\x00'):
            val = line.decode('utf-8')
            if val:
                eq = val.index('=')
                d[val[0:eq]] = val[eq + 1:]

        del elf
        f.close()
        return d

    def fetch_registers(self, thread: gdb.InferiorThread,
                        register: gdb.Register) -> None:
        if register is None:
            regnum = -1
        else:
            regnum = register.regnum
        self.arch.fetch_register(thread, regnum)

    def get_module_sections(self, module: gdb.Value) -> str:
        out = []
        for (name, addr) in for_each_module_section(module):
            out.append("-s {} {:#x}".format(name, addr))
        return " ".join(out)

    def check_module_version(self, modpath: str, module: gdb.Value) -> None:
        modinfo = self.extract_modinfo_from_module(modpath)

        vermagic = None
        if 'vermagic' in modinfo:
            vermagic = modinfo['vermagic']

        if vermagic != self.vermagic:
            raise ModVersionMismatchError(modpath, vermagic, self.vermagic)

        mi_srcversion = None
        if 'srcversion' in modinfo:
            mi_srcversion = modinfo['srcversion']

        mod_srcversion = None
        if 'srcversion' in module.type:
            mod_srcversion = module['srcversion'].string()

        if mi_srcversion != mod_srcversion:
            raise ModSourceVersionMismatchError(modpath, mi_srcversion,
                                                mod_srcversion)

    def load_modules(self, verbose: bool = False, debug: bool = False) -> None:
        import crash.cache.syscache
        version = crash.cache.syscache.utsname.release
        print("Loading modules for {}".format(version), end='')
        if verbose:
            print(":", flush=True)
        failed = 0
        loaded = 0
        for module in for_each_module():
            modname = "{}".format(module['name'].string())
            modfname = "{}.ko".format(modname)
            found = False
            for path in self.module_path:

                try:
                    modpath = self.find_module_file(modfname, path)
                except NoMatchingFileError:
                    continue

                try:
                    self.check_module_version(modpath, module)
                except ModinfoMismatchError as e:
                    if verbose:
                        print(str(e))
                    continue

                found = True

                if 'module_core' in module.type:
                    addr = int(module['module_core'])
                else:
                    addr = int(module['core_layout']['base'])

                if debug:
                    print("Loading {} at {:#x}".format(modpath, addr))
                elif verbose:
                    print("Loading {} at {:#x}".format(modname, addr))
                else:
                    print(".", end='')
                    sys.stdout.flush()

                sections = self.get_module_sections(module)

                percpu = int(module['percpu'])
                if percpu > 0:
                    sections += " -s .data..percpu {:#x}".format(percpu)

                try:
                    result = gdb.execute("add-symbol-file {} {:#x} {}"
                                         .format(modpath, addr, sections),
                                         to_string=True)
                except gdb.error as e:
                    raise CrashKernelError("Error while loading module `{}': {}"
                                           .format(modname, str(e)))
                if debug:
                    print(result)

                objfile = gdb.lookup_objfile(modpath)
                if not objfile.has_symbols():
                    self.load_module_debuginfo(objfile, modpath, verbose)
                elif debug:
                    print(" + has debug symbols")

                break

            if not found:
                if failed == 0:
                    print()
                print("Couldn't find module file for {}".format(modname))
                failed += 1
            else:
                if not objfile.has_symbols():
                    print("Couldn't find debuginfo for {}".format(modname))
                loaded += 1
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

    @staticmethod
    def normalize_modname(mod: str) -> str:
        return mod.replace('-', '_')

    def cache_modules_order(self, path: str) -> None:
        self.modules_order[path] = dict()
        order = os.path.join(path, "modules.order")
        try:
            f = open(order)
            for line in f.readlines():
                modpath = line.rstrip()
                modname = self.normalize_modname(os.path.basename(modpath))
                if modname[:7] == "kernel/":
                    modname = modname[7:]
                modpath = os.path.join(path, modpath)
                if os.path.exists(modpath):
                    self.modules_order[path][modname] = modpath
            f.close()
        except OSError:
            pass

    def get_module_path_from_modules_order(self, path: str, name: str) -> str:
        if not path in self.modules_order:
            self.cache_modules_order(path)

        try:
            return self.modules_order[path][name]
        except KeyError:
            raise NoMatchingFileError(name)

    def cache_file_tree(self, path: str, regex: Pattern[str] = None) -> None:
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
                modname = self.normalize_modname(filename)

                if regex and regex.match(modname) is None:
                    continue

                modpath = os.path.join(root, filename)
                self.findmap[path]['files'][modname] = modpath

    def get_file_path_from_tree_search(self, path: str, name: str,
                                       regex: Pattern[str] = None) -> str:
        self.cache_file_tree(path, regex)

        try:
            modname = self.normalize_modname(name)
            return self.findmap[path]['files'][modname]
        except KeyError:
            raise NoMatchingFileError(name)

    def find_module_file(self, name: str, path: str) -> str:
        try:
            return self.get_module_path_from_modules_order(path, name)
        except NoMatchingFileError:
            pass

        regex = re.compile(fnmatch.translate("*.ko"))
        return self.get_file_path_from_tree_search(path, name, regex)

    def find_module_debuginfo_file(self, name: str, path: str) -> str:
        regex = re.compile(fnmatch.translate("*.ko.debug"))
        return self.get_file_path_from_tree_search(path, name, regex)

    @staticmethod
    def build_id_path(objfile: gdb.Objfile) -> str:
        build_id = objfile.build_id
        return ".build_id/{}/{}.debug".format(build_id[0:2], build_id[2:])

    def try_load_debuginfo(self, objfile: gdb.Objfile,
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

    def load_module_debuginfo(self, objfile: gdb.Objfile,
                              modpath: str = None,
                              verbose: bool = False) -> None:
        if modpath is None:
            modpath = objfile.filename
        if ".gz" in modpath:
            modpath = modpath.replace(".gz", "")
        filename = "{}.debug".format(os.path.basename(modpath))

        build_id_path = self.build_id_path(objfile)

        for path in self.module_debuginfo_path:
            filepath = "{}/{}".format(path, build_id_path)
            if self.try_load_debuginfo(objfile, filepath, verbose):
                break

            try:
                filepath = self.find_module_debuginfo_file(filename, path)
            except NoMatchingFileError:
                continue

            if self.try_load_debuginfo(objfile, filepath, verbose):
                break

    def setup_tasks(self) -> None:
        from crash.types.percpu import get_percpu_vars
        from crash.types.task import LinuxTask, for_each_all_tasks
        import crash.cache.tasks
        gdb.execute('set print thread-events 0')

        rqs = get_percpu_vars(self.symbols.runqueues)
        rqscurrs = {int(x["curr"]) : k for (k, x) in rqs.items()}

        print("Loading tasks...", end='')
        sys.stdout.flush()

        task_count = 0
        try:
            crashing_cpu = int(get_symbol_value('crashing_cpu'))
        except MissingSymbolError:
            crashing_cpu = -1

        for task in for_each_all_tasks():
            ltask = LinuxTask(task)

            active = int(task.address) in rqscurrs
            if active:
                cpu = rqscurrs[int(task.address)]
                regs = self.vmcore.attr.cpu[cpu].reg
                ltask.set_active(cpu, regs)


            ptid = (LINUX_KERNEL_PID, task['pid'], 0)

            try:
                thread = gdb.selected_inferior().new_thread(ptid, ltask)
            except gdb.error:
                print("Failed to setup task @{:#x}".format(int(task.address)))
                continue
            thread.name = task['comm'].string()
            if active and cpu == crashing_cpu:
                self.crashing_thread = thread

            self.arch.setup_thread_info(thread)
            ltask.attach_thread(thread)
            ltask.set_get_stack_pointer(self.arch.get_stack_pointer)

            crash.cache.tasks.cache_task(ltask)

            task_count += 1
            if task_count % 100 == 0:
                print(".", end='')
                sys.stdout.flush()
        print(" done. ({} tasks total)".format(task_count))

        gdb.selected_inferior().executing = False
