# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
import os.path
from crash.infra import exporter, export, delayed_init
from crash.types.list import list_for_each_entry

if sys.version_info.major >= 3:
    long = int

@exporter
@delayed_init
class CrashKernel(object):
    def __init__(self):
        self.modules = gdb.lookup_symbol('modules', None)[0].value()
        self.module_type = gdb.lookup_type('struct module')
        self.findmap = {}

    @export
    def for_each_module(self):
        for module in list_for_each_entry(self.modules, self.module_type,
                                          'list'):
            yield module

    @export
    @staticmethod
    def get_module_sections(module):
        attrs = module['sect_attrs']
        out = []
        for sec in range(0, attrs['nsections']):
            attr = attrs['attrs'][sec]
            name = attr['name'].string()
            if name == '.text':
                continue
            out.append("-s {} {:#x}".format(name, long(attr['address'])))

        return " ".join(out)

    @export
    def load_modules(self, searchpath, verbose=False):
        print("Loading modules...", end='')
        sys.stdout.flush()
        failed = 0
        loaded = 0
        for module in for_each_module():
            modname = "{}".format(module['name'].string())
            modfname = "{}.ko".format(modname)
            found = False
            for path in searchpath:
                modpath = self.find_module_file(modfname, path)
                if not modpath:
                    continue

                found = True

                if verbose:
                    print("Loading {} at {}"
                          .format(modname, module['module_core']))
                sections = get_module_sections(module)
                gdb.execute("add-symbol-file {} {} {}"
                            .format(modpath, module['module_core'], sections),
                            to_string=True)
                objfile = gdb.lookup_objfile(modpath)
                load_debuginfo(searchpath, objfile, modpath)

                # We really should check the version, but GDB doesn't export
                # a way to lookup sections.
                break

            if not found:
                if failed == 0:
                    print()
                print("Couldn't find module file for {}".format(modname))
                failed += 1
            else:
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

    def find_module_file(self, name, path):
        if not path in self.findmap:
            self.findmap[path] = {}

            for root, dirs, files in os.walk(path):
                for filename in files:
                    nname = filename.replace('-', '_')
                    self.findmap[path][nname] = os.path.join(root, filename)
        try:
            return self.findmap[path][name]
        except KeyError:
            return None

    @export
    def load_debuginfo(self, searchpath, objfile, name=None, verbose=False):
        if name is None:
            name = objfile.filename
        if ".gz" in name:
            name = name.replace(".gz", "")
        filename = "{}.debug".format(os.path.basename(name))
        filepath = None

        # Check current directory first
        if os.path.exists(filename):
            filepath = filename
        else:
            for path in searchpath:
                filepath = self.find_module_file(filename, path)
                if filepath:
                    break

        if filepath:
            print("Found debuginfo for {}".format(name))
            objfile.add_separate_debug_file(filepath)
