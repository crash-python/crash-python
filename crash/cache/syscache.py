# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from crash.exceptions import MissingSymbolError
from crash.cache import CrashCache
from crash.infra import delayed_init

@delayed_init
class CrashUtsnameCache(CrashCache):
    def __init__(self):
        # Can't use super() with @delayed_init
        CrashCache.__init__(self)


        sym = gdb.lookup_global_symbol('init_uts_ns')
        if not sym:
            raise MissingSymbolError("CrashUtsnameCache requires init_uts_ns")
        init_uts_ns = sym.value()
        self.utsname = init_uts_ns['name']

        self.utsname_cache = {}

        for field in self.utsname.type.fields():
            val = self.utsname[field.name].string()
            self.utsname_cache[field.name] = val

    def __getattr__(self, name):
        if name in self.utsname_cache:
            return self.utsname_cache[name]
        raise AttributeError

utsname = CrashUtsnameCache()
