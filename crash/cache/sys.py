#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.cache import CrashCache

class GetSymbolException(Exception):
    pass

class GetValueException(Exception):
    pass

class CrashCacheSys(CrashCache):

    utsname_cache = None

    def init_utsname_cache(self):
        if self.utsname_cache:
            return

        try:
            init_uts_ns = gdb.lookup_global_symbol('init_uts_ns').value()
            utsname = init_uts_ns['name']
        except Exception, e:
            print "Error: Unable to locate utsname: %s" % (e)
            raise GetSymbolException(e)

        try:
            self.utsname_cache = dict()
            self.utsname_cache['nodename'] = utsname['nodename'].string()
            self.utsname_cache['release'] = utsname['release'].string()
            self.utsname_cache['version'] = utsname['version'].string()
            self.utsname_cache['machine'] = utsname['machine'].string()
        except Exception, e:
            print "Error: Unable to locate utsname string: %s" % (e)
            raise GetValueException(e)

    def init_sys_caches(self):
        self.init_utsname_cache()

    def __init__(self):
        super(CrashCacheSys, self).__init__()

    def refresh(self):
        pass

cache = CrashCacheSys()
