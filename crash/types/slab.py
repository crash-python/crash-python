#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of
from crash.types.list import list_for_each_entry

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
    def __populate_free(self):
        bufctl = self.gdb_obj.address[1].cast(bufctl_type).address
        bufsize = self.kmem_cache.buffer_size
        objs_per_slab = self.kmem_cache.objs_per_slab

        f = int(self.gdb_obj["free"])
        # print "free = " + str(f)
        while f != BUFCTL_END:
            if f >= objs_per_slab:
                print "bufctl value overflow"
                break

            self.free.add(self.s_mem + f * bufsize)

            if len(self.free) > objs_per_slab:
                print "bufctl cycle detected"
                break

            f = int(bufctl[f])
            # print f

    def check(self, slab_type):
        self.__populate_free()
        return len(self.free)
            
    def __init__(self, gdb_obj, kmem_cache):
        self.gdb_obj = gdb_obj
        self.kmem_cache = kmem_cache
        self.free = set()

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

    def __init__(self, name, gdb_obj):
        self.name = name
        self.gdb_obj = gdb_obj
        
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
                break

            # A node cannot have alien cache on the same node, but some
            # kernels (xen) seem to have a non-null pointer there anyway
            if ac_type == AC_ALIEN and nid_src == i:
                break

            res.update(self.__get_array_cache(ptr.dereference(), ac_type,
                        nid_src, i))

        return res

    def get_all_array_caches(self):
        res = dict()

        percpu_cache = self.gdb_obj["array"]
        res.update(self.__get_array_caches(percpu_cache, AC_PERCPU, -1, nr_cpu_ids))

        # TODO check and report collisions
        for (nid, node) in self.__get_nodelists():
            shared_cache = node["shared"]
            res.update(self.__get_array_cache(shared_cache, AC_SHARED, nid, nid))
            alien_cache = node["alien"]
            # TODO check that this only happens for single-node systems?
            if long(alien_cache) == 0L:
                continue
            res.update(self.__get_array_caches(alien_cache, AC_ALIEN, nid, nr_node_ids))

        return res

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

