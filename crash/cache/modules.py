#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
import os
import gdb
import sys
from crash.cache import CrashCache
from crash.types.list import list_for_each_entry

if sys.version_info.major >= 3:
    long = int

class Kmod():
    def __init__(self, obj):
        self.name = obj['name'].string()
        self.objfile = None
        self._module = obj

    def get_base_addr(self):
        return long(self._module.address)

    def get_size(self):
        return long(self._module['core_size'])

    def load_objfile(self, path):
        self.objfile = os.path.abspath(path)
        try:
            gdb.execute("add-symbol-file {} {}".format(path, self._module['module_core']))
        except gdb.error:
            self.objfile = None
            print("Error adding symbol informatation")

class KmodCache(CrashCache):
    def __init__(self):
        super(KmodCache, self).__init__()
        self._modules = {}
        self._cache_init = False

    def init_modules_cache(self):
        if self._cache_init: return

        module_type = gdb.lookup_type('struct module')
        modules = gdb.lookup_symbol('modules', None)[0].value()
        for module in list_for_each_entry(modules, module_type, 'list'):
            kmod = Kmod(module)
            self._modules[kmod.name] = kmod

        self._cache_init = True

    def __len__(self):
        return len(self._modules)

    def __getitem__(self, key):
        return self._modules[key]

    def __contains__(self, item):
        return item in self._modules

    def __iter__(self):
        return self._modules.__iter__()

    def values(self):
        return self._modules.values()

cache = KmodCache()


