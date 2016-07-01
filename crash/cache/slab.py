#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.types.list import list_for_each_entry
from crash.types.slab import KmemCache, kmem_cache_type
from crash.cache import CrashCache

def dump(obj):
  for attr in dir(obj):
    print "obj.%s = %s" % (attr, getattr(obj, attr))

def get_value(name):
    sym = gdb.lookup_symbol(name, None)[0]
    
    if sym:
        return sym.value()

    return None

class CrashCacheSlab(CrashCache):

    def __init_kmem_caches(self):
        if self.kmem_caches:
            return

        list_caches = get_value("slab_caches")

        if not list_caches:
            list_caches = get_value("cache_chain")

        # TODO exception if still None

        for cache in list_for_each_entry(list_caches, kmem_cache_type, "next"):
            name = cache["name"].string()
            kmem_cache = KmemCache(name, cache)
 
            self.kmem_caches[name] = kmem_cache
            self.kmem_caches_by_addr[long(cache.address)] = kmem_cache

    def get_kmem_caches(self):
        self.__init_kmem_caches()
        return self.kmem_caches

    def get_kmem_cache(self, name):
        return self.get_kmem_caches()[name]

    def get_kmem_cache_addr(self, addr):
        self.__init_kmem_caches()
        return self.kmem_caches_by_addr[addr]

    def __init__(self):
        super(CrashCacheSlab, self).__init__()
        self.kmem_caches = dict()
        self.kmem_caches_by_addr = dict()

    def refresh(self):
        pass

cache = CrashCacheSlab()
