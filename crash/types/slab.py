#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of

kmem_cache_type = gdb.lookup_type('struct kmem_cache')

AC_PERCPU = "percpu"
AC_SHARED = "shared"
AC_ALIEN  = "alien"

class KmemCache():
    gdb_obj = None

    num = 0
    buffer_size = 0
    name = ""

    def __get_nodelist(self, node):
        return self.gdb_obj["nodelists"][node]
        
    def __get_nodelists(self):
        # TODO use real number of nodes
        i = 0;
        while True:
            node = self.__get_nodelist(i)
            if long(node) == 0L:
                break
            yield node
            i += 1

    def __init__(self, name, gdb_obj):
        self.name = name
        self.gdb_obj = gdb_obj
        
        self.num = int(gdb_obj["num"])
        self.buffer_size = int(gdb_obj["buffer_size"])

    def __get_array_cache(self, acache, ac_type, nid_src, nid_tgt):
        res = dict()
        
        avail = int(acache["avail"])
        limit = int(acache["limit"])

        # TODO check avail > limit
        if avail == 0:
            return res

        for i in range(0, avail - 1):
            ptr = long(acache["entry"][i])
            res[ptr] = {"ac_type" : ac_type, "nid_src" : nid_src,
                        "nid_tgt" : nid_tgt}

        return res

    def __get_array_caches(self, array, ac_type, nid_src):
        res = dict()

        i = 0;
        while True:
            ptr = array[i]

            if long(ptr) == 0L:
                break

            # A node cannot have alien cache on the same node, but some
            # kernels (xen) seem to have a non-null pointer there anyway
            if ac_type == AC_ALIEN and nid_src == i:
                break

            if ac_type == AC_SHARED:
                nid_tgt = -1
            else:
                nid_tgt = i

            res.update(self.__get_array_cache(ptr.dereference(), ac_type,
                        nid_src, nid_tgt))

            i += 1

        return res

    def get_all_array_caches(self):
        res = dict()

        percpu_cache = self.gdb_obj["array"]
        res.update(self.__get_array_caches(percpu_cache, AC_PERCPU, -1))

        return res
