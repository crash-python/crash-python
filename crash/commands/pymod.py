#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import gdb
import argparse
import sys
from crash.types.list import list_for_each_entry
from crash.commands import CrashCommand
from crash.cache import modules

if sys.version_info.major >= 3:
    long = int

class ModCommand(CrashCommand):
    """
    """
    def __init__(self, name):
        #init parser
        parser = argparse.ArgumentParser(prog=name)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-s", metavar="module")
        parser.add_argument('args', nargs='*')
        #initialize module cache

        CrashCommand.__init__(self, "mod", parser)

    def _list_modules(self):
        modules_sorted = []
        sort_by_addr = lambda x: long(x.get_base_addr())

        print("{0:^16} {1:<16} {2:<8} OBJECT FILE".format("MODULE", "NAME", "SIZE"))

        for module in sorted(modules.cache.values(), key=sort_by_addr):
            objfile = module.objfile
            if objfile is None:
                objfile = "(not loaded)"
            print("{0:^16x} {1:<16} {2:<8} {3}".format(long(module.get_base_addr()), module.name, module.get_size(), objfile))

    def _add_objfile(self, module_name, objfile_path):
        #Add handling for not loaded module, results in KeyError
        kmod = modules.cache[module_name]
        kmod.load_objfile(objfile_path)

    def execute(self, argv):
        modules.cache.init_modules_cache()
        if argv.s is not None:
            module_name = argv.s
            if len(argv.args):
                objfile = argv.args[0]
                self._add_objfile(module_name, objfile)
            else:
                #TODO: Automatically search for the module, perhaps
                #merge the stuff from contrib/mod.py
                pass
        else:
            self._list_modules()

ModCommand("mod")
