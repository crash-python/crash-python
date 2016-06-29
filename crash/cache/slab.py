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

    kmem_caches = None
    array_caches = None

    def __fill_all_array_caches(self, kmem_cache):
        array_caches[kmem_cache.name] = kmem_cache.get_all_array_caches()

    def init_kmem_caches(self):
        if self.kmem_caches:
            return

        list_caches = get_value("slab_caches")

        if not list_caches:
            list_caches = get_value("cache_chain")

        # TODO exception if still None

        self.kmem_caches = dict()
        for cache in list_for_each_entry(list_caches, kmem_cache_type, "next"):
            name = cache["name"].string()
            self.kmem_caches[name] = KmemCache(name, cache)

    def __init__(self):
        super(CrashCacheSlab, self).__init__()

    def refresh(self):
        pass

cache = CrashCacheSlab()
