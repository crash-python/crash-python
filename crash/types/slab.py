#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import crash
from util import container_of, find_member_variant, safe_lookup_type, get_symbol_value
from util import safe_get_symbol_value
from percpu import get_percpu_var
from crash.types.list import list_for_each_entry
from crash.types.page import Page
from crash.types.node import Node
from crash.types.cpu import for_each_online_cpu
from crash.cache.slab import cache as caches_cache

kmem_cache_type = gdb.lookup_type("struct kmem_cache")

slab_type = safe_lookup_type("struct slab")
slab_list_head = "list"
page_slab = False
if slab_type is None:
    slab_type = gdb.lookup_type("struct page")
    slab_list_head = "lru"
    page_slab = True

bufctl_type = safe_lookup_type("kmem_bufctl_t")
if bufctl_type is None:
    bufctl_type = safe_lookup_type("freelist_idx_t")

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
        kmem_cache = KmemCache.from_addr(kmem_cache_addr)
        if page_slab:
            return Slab(page.gdb_obj, kmem_cache)
        else:
            slab_addr = long(page.get_slab_page())
            return Slab.from_addr(slab_addr, kmem_cache)

    @staticmethod
    def from_obj(addr):
        page = Page.from_addr(addr).compound_head()
        if not page.is_slab():
            return None

        return Slab.from_page(page)

    def __add_free_obj_by_idx(self, idx):
        objs_per_slab = self.kmem_cache.objs_per_slab
        bufsize = self.kmem_cache.buffer_size
        
        if (idx >= objs_per_slab):
            self.__error(": free object index %d overflows %d" % (idx,
                                                            objs_per_slab))
            return False

        obj_addr = self.s_mem + idx * bufsize
        if obj_addr in self.free:
            self.__error(": object %x duplicated on freelist" % obj_addr)
            return False
        else:
            self.free.add(obj_addr)
        
        return True

    def __populate_free(self):
        if self.free:
            return
        
        self.free = set()
        bufsize = self.kmem_cache.buffer_size
        objs_per_slab = self.kmem_cache.objs_per_slab

        if page_slab:
            page = self.gdb_obj
            freelist = page["freelist"].cast(bufctl_type.pointer())
            for i in range(self.inuse, objs_per_slab):
                obj_idx  = int(freelist[i])
                self.__add_free_obj_by_idx(obj_idx)

        else:
            bufctl = self.gdb_obj.address[1].cast(bufctl_type).address
            f = int(self.gdb_obj["free"])
            while f != BUFCTL_END:
                if not self.__add_free_obj_by_idx(f):
                    self.__error(": bufctl cycle detected")
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
            return (False, obj_addr, ac[obj_addr])

        return (True, obj_addr, None)
    
    def __error(self, msg):
        print ("cache %s slab %x%s" % (self.kmem_cache.name,
                    long(self.gdb_obj.address), msg))
 
    def __free_error(self, list_name):
        self.__error(": is on list %s, but has %d of %d objects allocated" %
                (list_name, len(self.free), self.kmem_cache.objs_per_slab))

    def get_objects(self):
        bufsize = self.kmem_cache.buffer_size
        obj = self.s_mem
        for i in range(self.kmem_cache.objs_per_slab):
            yield obj
            obj += bufsize

    def get_allocated_objects(self):
        for obj in self.get_objects():
            c = self.contains_obj(obj)
            if c[0]:
                yield obj

    def check(self, slabtype):
        self.__populate_free()
        num_free = len(self.free)
        max_free = self.kmem_cache.objs_per_slab

        if self.inuse + num_free != max_free:
            self.__error(": inuse=%d free=%d adds up to %d (should be %d)" %
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
                self.__error(": obj %x is marked as free but in array cache:" % obj)
                print(ac[obj])
            page = Page.from_addr(obj).compound_head()
            if not page.is_slab():
                self.__error(": obj %x is not on PageSlab page" % obj)
            kmem_cache_addr = long(page.get_slab_cache())
            if kmem_cache_addr != long(self.kmem_cache.gdb_obj.address):
                self.__error(": obj %x is on page where pointer to kmem_cache points to %x instead of %x" %
                                            (obj, kmem_cache_addr, long(self.kmem_cache.gdb_obj.address)))

            if page_slab:
                continue

            slab_addr = long(page.get_slab_page())
            if slab_addr != self.gdb_obj.address:
                self.__error(": obj %x is on page where pointer to slab wrongly points to %x" %
                                                                        (obj, slab_addr))
        return num_free
            
    def __init__(self, gdb_obj, kmem_cache):
        self.gdb_obj = gdb_obj
        self.kmem_cache = kmem_cache
        self.free = None

        if page_slab:
            self.inuse = int(gdb_obj["active"])
        else:
            self.inuse = int(gdb_obj["inuse"])
        self.s_mem = long(gdb_obj["s_mem"])

class KmemCache:

    buffer_size_name = find_member_variant(kmem_cache_type,
                                        ("buffer_size", "size"))
    nodelists_name = find_member_variant(kmem_cache_type,
                                        ("nodelists", "node"))

    percpu_name = find_member_variant(kmem_cache_type,
                                        ("cpu_cache", "array"))

    percpu_cache = bool(percpu_name == "cpu_cache")

    alien_cache_type = safe_lookup_type("struct alien_cache");

    def __get_nodelist(self, node):
        return self.gdb_obj[KmemCache.nodelists_name][node]
        
    def __get_nodelists(self):
        for nid in Node.for_each_nid():
            node = self.__get_nodelist(nid)
            if long(node) == 0L:
                continue
            yield (nid, node.dereference())

    @staticmethod
    def __init_kmem_caches():
        if caches_cache.populated:
            return

        list_caches = safe_get_symbol_value("slab_caches")

        if not list_caches:
            list_caches = safe_get_symbol_value("cache_chain")

        head_name = find_member_variant(kmem_cache_type, ("next", "list"))

        for cache in list_for_each_entry(list_caches, kmem_cache_type,
                                                                head_name):
            name = cache["name"].string()
            kmem_cache = KmemCache(name, cache)
 
            caches_cache.kmem_caches[name] = kmem_cache
            caches_cache.kmem_caches_by_addr[long(cache.address)] = kmem_cache

        caches_cache.populated = True

    @staticmethod
    def from_addr(addr):
        if not addr in caches_cache.kmem_caches_by_addr:
            KmemCache.__init_kmem_caches()
            
        return caches_cache.kmem_caches_by_addr[addr]

    @staticmethod
    def from_name(name):
        KmemCache.__init_kmem_caches()
        return caches_cache.kmem_caches[name]

    @staticmethod
    def get_all_caches():
        KmemCache.__init_kmem_caches()
        return caches_cache.kmem_caches.values()

    def __init__(self, name, gdb_obj):
        self.name = name
        self.gdb_obj = gdb_obj
        self.array_caches = None
        
        self.objs_per_slab = int(gdb_obj["num"])
        self.buffer_size = int(gdb_obj[KmemCache.buffer_size_name])

    def __fill_array_cache(self, acache, ac_type, nid_src, nid_tgt):
        avail = int(acache["avail"])
        limit = int(acache["limit"])

        # TODO check avail > limit
        if avail == 0:
            return

        cache_dict = {"ac_type" : ac_type, "nid_src" : nid_src,
                        "nid_tgt" : nid_tgt}

        for i in range(avail):
            ptr = long(acache["entry"][i])
            if ptr in self.array_caches:
                print ("WARNING: array cache duplicity detected!")
            else:
                self.array_caches[ptr] = cache_dict

    def __fill_alien_caches(self, node, nid_src):
        alien_cache = node["alien"]

        # TODO check that this only happens for single-node systems?
        if long(alien_cache) == 0L:
            return

        for nid in Node.for_each_nid():
            array = alien_cache[nid].dereference()

            # TODO: limit should prevent this?
            if array.address == 0:
                continue

            if KmemCache.alien_cache_type is not None:
                array = array["ac"]

            # A node cannot have alien cache on the same node, but some
            # kernels (xen) seem to have a non-null pointer there anyway
            if nid_src == nid:
                continue

            self.__fill_array_cache(array, AC_ALIEN, nid_src, nid)

    def __fill_percpu_caches(self):
        cpu_cache = self.gdb_obj[KmemCache.percpu_name]

        for cpu in for_each_online_cpu():
            if (KmemCache.percpu_cache):
                array = get_percpu_var(cpu_cache, cpu)
            else:
                array = cpu_cache[cpu].dereference()

            self.__fill_array_cache(array, AC_PERCPU, -1, cpu)

    def __fill_all_array_caches(self):
        self.array_caches = dict()

        self.__fill_percpu_caches()

        # TODO check and report collisions
        for (nid, node) in self.__get_nodelists():
            shared_cache = node["shared"]
            if long(shared_cache) != 0:
                self.__fill_array_cache(shared_cache.dereference(), AC_SHARED, nid, nid)
            
            self.__fill_alien_caches(node, nid)

    def get_array_caches(self):
        if self.array_caches is None:
            self.__fill_all_array_caches()

        return self.array_caches

    def __get_allocated_objects(self, slab_list):
        for gdb_slab in list_for_each_entry(slab_list, slab_type, slab_list_head):
            slab = Slab(gdb_slab, self)
            for obj in slab.get_allocated_objects():
                yield obj

    def get_allocated_objects(self):
        for (nid, node) in self.__get_nodelists():
            for obj in self.__get_allocated_objects(node["slabs_partial"]):
                yield obj
            for obj in self.__get_allocated_objects(node["slabs_full"]):
                yield obj

    def __check_slabs(self, slab_list, slabtype):
        free = 0
        for gdb_slab in list_for_each_entry(slab_list, slab_type, slab_list_head):
            slab = Slab(gdb_slab, self)
            free += slab.check(slabtype)
        #TODO: check if array cache contains bogus pointers or free objects
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

