#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import crash
from util import container_of
from crash.types.list import list_for_each_entry
from crash.types.page import Page

kmem_cache_type = gdb.lookup_type("struct kmem_cache")
slab_type = gdb.lookup_type("struct slab")
bufctl_type = gdb.lookup_type("kmem_bufctl_t")

# TODO abstract away
nr_cpu_ids = long(gdb.lookup_global_symbol("nr_cpu_ids").value())
nr_node_ids = long(gdb.lookup_global_symbol("nr_node_ids").value())

AC_PERCPU = "percpu"
AC_SHARED = "shared"
AC_ALIEN  = "alien"

slab_partial = 0
slab_full = 1
slab_free = 3

BUFCTL_END = ~0 & 0xffffffff

class Slab:
    @staticmethod
    def from_addr(slab_addr, kmem_cache):
        if not isinstance(kmem_cache, KmemCache):
            kmem_cache = KmemCache.from_addr(kmem_cache)
        slab_struct = gdb.Value(slab_addr).cast(slab_type.pointer()).dereference()
        return Slab(slab_struct, kmem_cache)

    @staticmethod
    def from_page(page):
        kmem_cache_addr = long(page.gdb_obj["lru"]["next"])
        slab_addr = long(page.gdb_obj["lru"]["prev"])
        return Slab.from_addr(slab_addr, kmem_cache_addr)

    @staticmethod
    def from_obj(addr):
        page = Page.from_addr(addr).compound_head()
        if not page.is_slab():
            return None

        return Slab.from_page(page)

    def __populate_free(self):
        if self.free:
            return
        
        self.free = set()
        bufctl = self.gdb_obj.address[1].cast(bufctl_type).address
        bufsize = self.kmem_cache.buffer_size
        objs_per_slab = self.kmem_cache.objs_per_slab

        f = int(self.gdb_obj["free"])
        while f != BUFCTL_END:
            if f >= objs_per_slab:
                print "bufctl value overflow"
                break

            self.free.add(self.s_mem + f * bufsize)

            if len(self.free) > objs_per_slab:
                print "bufctl cycle detected"
                break

            f = int(bufctl[f])

    def find_obj(self, addr):
        bufsize = self.kmem_cache.buffer_size
        objs_per_slab = self.kmem_cache.objs_per_slab
        
        if long(addr) < self.s_mem:
            return None

        idx = (long(addr) - self.s_mem) / bufsize
        if idx >= objs_per_slab:
            return None

        return self.s_mem + (idx * bufsize)

    def contains_obj(self, addr):
        obj_addr = self.find_obj(addr)

        if not obj_addr:
            return (False, 0L, None)

        self.__populate_free()
        if obj_addr in self.free:
            return (False, obj_addr, None)

        ac = self.kmem_cache.get_array_caches()

        if obj_addr in ac:
            return (False, obj_addr, ac)

        return (True, obj_addr, None)
        

    def check(self, slab_type):
        self.__populate_free()
        return len(self.free)
            
    def __init__(self, gdb_obj, kmem_cache):
        self.gdb_obj = gdb_obj
        self.kmem_cache = kmem_cache
        self.free = None

        self.inuse = int(gdb_obj["inuse"])
        self.s_mem = long(gdb_obj["s_mem"])

class KmemCache:
    def __get_nodelist(self, node):
        return self.gdb_obj["nodelists"][node]
        
    def __get_nodelists(self):
        for i in range(nr_node_ids):
            node = self.__get_nodelist(i)
            if long(node) == 0L:
                continue
            yield (i, node.dereference())

    @staticmethod
    def from_addr(addr):
        return crash.cache.slab.cache.get_kmem_cache_addr(addr)

    @staticmethod
    def from_name(name):
        return crash.cache.slab.cache.get_kmem_cache(name)

    @staticmethod
    def get_all_caches():
        return crash.cache.slab.cache.get_kmem_caches().values()

    def __init__(self, name, gdb_obj):
        self.name = name
        self.gdb_obj = gdb_obj
        self.array_caches = None
        
        self.objs_per_slab = int(gdb_obj["num"])
        self.buffer_size = int(gdb_obj["buffer_size"])

    def __get_array_cache(self, acache, ac_type, nid_src, nid_tgt):
        res = dict()

        avail = int(acache["avail"])
        limit = int(acache["limit"])

        # TODO check avail > limit
        if avail == 0:
            return res

        cache_dict = {"ac_type" : ac_type, "nid_src" : nid_src,
                        "nid_tgt" : nid_tgt}

        for i in range(avail):
            ptr = long(acache["entry"][i])
            res[ptr] = cache_dict

        return res

    def __get_array_caches(self, array, ac_type, nid_src, limit):
        res = dict()

        for i in range(limit):
            ptr = array[i]

            # TODO: limit should prevent this?
            if long(ptr) == 0L:
                continue

            # A node cannot have alien cache on the same node, but some
            # kernels (xen) seem to have a non-null pointer there anyway
            if ac_type == AC_ALIEN and nid_src == i:
                continue

            res.update(self.__get_array_cache(ptr.dereference(), ac_type,
                        nid_src, i))

        return res

    def __fill_array_caches(self):
        res = dict()

        percpu_cache = self.gdb_obj["array"]
        res.update(self.__get_array_caches(percpu_cache, AC_PERCPU, -1, nr_cpu_ids))

        # TODO check and report collisions
        for (nid, node) in self.__get_nodelists():
            shared_cache = node["shared"]
            if long(shared_cache) != 0:
                res.update(self.__get_array_cache(shared_cache.dereference(), AC_SHARED, nid, nid))
            alien_cache = node["alien"]
            # TODO check that this only happens for single-node systems?
            if long(alien_cache) == 0L:
                continue
            res.update(self.__get_array_caches(alien_cache, AC_ALIEN, nid, nr_node_ids))

        self.array_caches = res

    def get_array_caches(self):
        if not self.array_caches:
            self.__fill_array_caches()

        return self.array_caches

    def __check_slabs(self, slab_list, slabtype):
        free = 0
        for gdb_slab in list_for_each_entry(slab_list, slab_type, "list"):
            slab = Slab(gdb_slab, self)
            free += slab.check(slabtype)
        return free

    def check_all(self):
        for (nid, node) in self.__get_nodelists():
            free_declared = long(node["free_objects"])
            free_counted = self.__check_slabs(node["slabs_partial"], slab_partial)
            free_counted += self.__check_slabs(node["slabs_full"], slab_full)
            free_counted += self.__check_slabs(node["slabs_free"], slab_free)
            if free_declared != free_counted:
                print "free counted doesn't match"

