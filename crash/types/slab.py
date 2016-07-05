#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import crash
from util import container_of, find_member_variant
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
slab_free = 2

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
        kmem_cache_addr = long(page.get_slab_cache())
        slab_addr = long(page.get_slab_page())
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
    
    def __error(self, msg):
        print ("cache %s slab %x%s" % (self.kmem_cache.name,
                    long(self.gdb_obj.address), msg))
 
    def __free_error(self, list_name):
        self.__error("is on list %s, but has %d/%d objects" %
                (list_name, len(self.free), self.kmem_cache.objs_per_slab))

    def get_objects(self):
        bufsize = self.kmem_cache.buffer_size
        obj = self.s_mem
        for i in range(self.kmem_cache.objs_per_slab):
            yield obj
            obj += bufsize

    def check(self, slabtype):
        self.__populate_free()
        num_free = len(self.free)
        max_free = self.kmem_cache.objs_per_slab

        if self.inuse + num_free != max_free:
            self.__error(": inuse=%d free=%d adds up to %d != %d" %
                    (self.inuse, num_free, self.inuse + num_free, max_free))
            
        if slabtype == slab_free:
            if num_free != max_free:
                self.__free_error("slab_free")
        elif slabtype == slab_partial:
            if num_free == 0 or num_free == max_free:
                self.__free_error("slab_partial")
        elif slabtype == slab_full:
            if num_free > 0:
                self.__free_error("slab_full")

        ac = self.kmem_cache.get_array_caches()
        for obj in self.get_objects():
            if obj in self.free and obj in ac:
                self.__error(": obj %x is marked as free but in array cache:")
                print(ac[obj])
            page = Page.from_addr(obj).compound_head()
            if not page.is_slab():
                self.__error(": obj %x is not on PageSlab page" % obj)
            kmem_cache_addr = long(page.get_slab_cache())
            if kmem_cache_addr != long(self.kmem_cache.gdb_obj.address):
                self.__error(": obj %x is on page where pointer to kmem_cache points to %x instead of %x" %
                                            (obj, kmem_cache_addr, long(self.kmem_cache.gdb_obj.address)))
            slab_addr = long(page.get_slab_page())
            if slab_addr != self.gdb_obj.address:
                self.__error(": obj %x is on page where pointer to slab wrongly points to %x" %
                                                                        (obj, slab_addr))
        return num_free
            
    def __init__(self, gdb_obj, kmem_cache):
        self.gdb_obj = gdb_obj
        self.kmem_cache = kmem_cache
        self.free = None

        self.inuse = int(gdb_obj["inuse"])
        self.s_mem = long(gdb_obj["s_mem"])

class KmemCache:

    buffer_size_name = find_member_variant(kmem_cache_type,
                                        ("buffer_size", "size"))
    nodelists_name = find_member_variant(kmem_cache_type,
                                        ("nodelists", "node"))
    def __get_nodelist(self, node):
        return self.gdb_obj[KmemCache.nodelists_name][node]
        
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
        self.buffer_size = int(gdb_obj[KmemCache.buffer_size_name])

    def __get_array_cache(self, acache, ac_type, nid_src, nid_tgt):
        avail = int(acache["avail"])
        limit = int(acache["limit"])

        # TODO check avail > limit
        if avail == 0:
            return

        cache_dict = {"ac_type" : ac_type, "nid_src" : nid_src,
                        "nid_tgt" : nid_tgt}

        for i in range(avail):
            ptr = long(acache["entry"][i])
            yield (ptr, cache_dict)

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

            for (ptr, cache_dict) in self.__get_array_cache(ptr.dereference(),
                                                        ac_type, nid_src, i):
                yield (ptr, cache_dict)

    def __fill_array_cache(self, add):
        for (ptr, cache_dict) in add:
            if ptr in self.array_caches:
                print ("WARNING: array cache duplicity detected!")
            else:
                self.array_caches[ptr] = cache_dict

    def __fill_array_caches(self):
        self.array_caches = dict()

        percpu_cache = self.gdb_obj["array"]

        add = self.__get_array_caches(percpu_cache, AC_PERCPU, -1, nr_cpu_ids)
        self.__fill_array_cache(add) 

        # TODO check and report collisions
        for (nid, node) in self.__get_nodelists():
            shared_cache = node["shared"]
            if long(shared_cache) != 0:
                add = self.__get_array_cache(shared_cache.dereference(), AC_SHARED, nid, nid)
                self.__fill_array_cache(add)
            alien_cache = node["alien"]
            # TODO check that this only happens for single-node systems?
            if long(alien_cache) == 0L:
                continue
            add = self.__get_array_caches(alien_cache, AC_ALIEN, nid, nr_node_ids)
            self.__fill_array_cache(add)

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
                print ("free objects mismatch: declared=%d counted=%d" %
                                                (free_declared, free_counted))

