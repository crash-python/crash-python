#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of

kmem_cache_type = gdb.lookup_type("struct kmem_cache")
slab_type = gdb.lookup_type("struct slab")
bufctlp_type = gdb.lookup_type("kmem_bufctl_t").pointer()

# TODO abstract away
nr_cpu_ids = long(gdb.lookup_global_symbol("nr_cpu_ids").value())
nr_node_ids = long(gdb.lookup_global_symbol("nr_node_ids").value())

AC_PERCPU = "percpu"
AC_SHARED = "shared"
AC_ALIEN  = "alien"

BUFCTL_END = ~0

class Slab:
    gdb_obj = None
    kmem_cache = None

    inuse = 0
    s_mem = 0L
    free = set()

    def __populate_free(self):
        bufctl = self.gdb.obj.address[1].cast(bufctlp_type).dereference()
        bufsize = self.kmem_cache.buffer_size
        objs_per_slab = self.kmem_cache.objs_per_slab

        f = int(self.gdb_obj["free"])
        while f != BUFCTL_END:
            if f >= objs_per_slab:
                print "bufctl value overflow"
                break

            free.add(s_mem + f * bufsize)
    
            if len(free) > objs_per_slab:
                print "bufctl cycle detected"
                break

            f = int(bufctl[f])
            
    def __init__(self, gdb_obj, kmem_cache):
        self.gdb_obj = gdb_obj
        self.kmem_cache = kmem_cache

        self.inuse = int(gdb_obj["inuse"])
        self.s_mem = long(gdb_obj["s_mem"])

class KmemCache:
    gdb_obj = None

    objs_per_slab = 0
    buffer_size = 0
    name = ""

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
