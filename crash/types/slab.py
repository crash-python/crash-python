#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import TypeVar, Union, Tuple, Iterable, Dict, Optional, Set
from typing import ValuesView

import sys
import traceback

from crash.util import container_of, find_member_variant
from crash.util.symbols import Types, TypeCallbacks, SymbolCallbacks
from crash.types.percpu import get_percpu_var
from crash.types.list import list_for_each, list_for_each_entry, ListError
from crash.types.page import page_from_gdb_obj, page_from_addr, Page
from crash.types.node import for_each_nid
from crash.types.cpu import for_each_online_cpu
from crash.types.node import numa_node_id

import gdb

AC_PERCPU = "percpu"
AC_SHARED = "shared"
AC_ALIEN = "alien"

slab_partial = 0
slab_full = 1
slab_free = 2

slab_list_name = {0: "partial", 1: "full", 2: "free"}
slab_list_fullname = {0: "slabs_partial", 1: "slabs_full", 2: "slabs_free"}

BUFCTL_END = ~0 & 0xffffffff

def col_error(msg: str) -> str:
    return "\033[1;31;40m {}\033[0;37;40m ".format(msg)

def col_bold(msg: str) -> str:
    return "\033[1;37;40m {}\033[0;37;40m ".format(msg)

types = Types(['kmem_cache', 'struct kmem_cache'])

SlabType = TypeVar('SlabType', bound='Slab')
KmemCacheType = TypeVar('KmemCacheType', bound='KmemCache')

class Slab:

    slab_list_head: str = 'list'
    page_slab: bool = False
    real_slab_type: gdb.Type = None
    bufctl_type: gdb.Type = None

    @classmethod
    def check_page_type(cls, gdbtype: gdb.Type) -> None:
        if cls.page_slab is False:
            cls.page_slab = True
            cls.real_slab_type = gdbtype
            cls.slab_list_head = 'lru'

    @classmethod
    def check_slab_type(cls, gdbtype: gdb.Type) -> None:
        cls.page_slab = False
        cls.real_slab_type = gdbtype
        cls.slab_list_head = 'list'

    @classmethod
    def check_bufctl_type(cls, gdbtype: gdb.Type) -> None:
        cls.bufctl_type = gdbtype

    @classmethod
    def from_addr(cls, slab_addr: int,
                  kmem_cache: Union[int, 'KmemCache']) -> 'Slab':
        if not isinstance(kmem_cache, KmemCache):
            kmem_cache = kmem_cache_from_addr(kmem_cache)
        slab_struct = gdb.Value(slab_addr).cast(cls.real_slab_type.pointer()).dereference()
        return cls(slab_struct, kmem_cache)

    @classmethod
    def from_page(cls, page: Page) -> 'Slab':
        kmem_cache_addr = int(page.get_slab_cache())
        kmem_cache = kmem_cache_from_addr(kmem_cache_addr)
        if kmem_cache is None:
            raise RuntimeError("No kmem cache found for page")
        if cls.page_slab:
            return cls(page.gdb_obj, kmem_cache)
        slab_addr = int(page.get_slab_page())
        return cls.from_addr(slab_addr, kmem_cache)

    @classmethod
    def from_list_head(cls, list_head: gdb.Value,
                       kmem_cache: 'KmemCache') -> 'Slab':
        gdb_obj = container_of(list_head, cls.real_slab_type, cls.slab_list_head)
        return cls(gdb_obj, kmem_cache)

    def __init__(self, gdb_obj: gdb.Value, kmem_cache: 'KmemCache',
                 error: bool = False) -> None:
        self.error = error
        self.gdb_obj = gdb_obj
        self.kmem_cache = kmem_cache
        self.free: Set[int] = set()
        self.misplaced_list: Optional[str]
        self.misplaced_error: Optional[str]

        self.misplaced_list = None
        self.misplaced_error = None

        if error:
            return

        if self.page_slab:
            self.inuse = int(gdb_obj["active"])
            self.page = page_from_gdb_obj(gdb_obj)
        else:
            self.inuse = int(gdb_obj["inuse"])
        self.s_mem = int(gdb_obj["s_mem"])

    def __add_free_obj_by_idx(self, idx: int) -> bool:
        objs_per_slab = self.kmem_cache.objs_per_slab
        bufsize = self.kmem_cache.buffer_size

        if idx >= objs_per_slab:
            self.__error(": free object index %d overflows %d" %
                         (idx, objs_per_slab))
            return False

        obj_addr = self.s_mem + idx * bufsize
        if obj_addr in self.free:
            self.__error(": object %x duplicated on freelist" % obj_addr)
            return False
        else:
            self.free.add(obj_addr)

        return True

    def __populate_free(self) -> None:
        if self.free:
            return

        objs_per_slab = self.kmem_cache.objs_per_slab

        if self.page_slab:
            page = self.gdb_obj
            freelist = page["freelist"].cast(self.bufctl_type.pointer())
            for i in range(self.inuse, objs_per_slab):
                obj_idx = int(freelist[i])
                self.__add_free_obj_by_idx(obj_idx)
            # XXX not generally useful and reliable
            if False and objs_per_slab > 1:
                all_zeroes = True
                for i in range(objs_per_slab):
                    obj_idx = int(freelist[i])
                    if obj_idx != 0:
                        all_zeroes = False
                if all_zeroes:
                    self.__error(": freelist full of zeroes")

        else:
            bufctl = self.gdb_obj.address[1].cast(self.bufctl_type).address
            f = int(self.gdb_obj["free"])
            while f != BUFCTL_END:
                if not self.__add_free_obj_by_idx(f):
                    self.__error(": bufctl cycle detected")
                    break

                f = int(bufctl[f])

    def find_obj(self, addr: int) -> Union[int, None]:
        bufsize = self.kmem_cache.buffer_size
        objs_per_slab = self.kmem_cache.objs_per_slab

        if int(addr) < self.s_mem:
            return None

        idx = (int(addr) - self.s_mem) // bufsize
        if idx >= objs_per_slab:
            return None

        return self.s_mem + (idx * bufsize)

    def contains_obj(self,
                     addr: int) -> Tuple[bool, int, Union[gdb.Value, None]]:
        obj_addr = self.find_obj(addr)

        if not obj_addr:
            return (False, 0, None)

        self.__populate_free()
        if obj_addr in self.free:
            return (False, int(obj_addr), None)

        ac = self.kmem_cache.get_array_caches()

        if obj_addr in ac:
            return (False, int(obj_addr), ac[obj_addr])

        return (True, int(obj_addr), None)

    def __error(self, msg: str, misplaced: bool = False) -> None:
        msg = col_error("cache %s slab %x%s" % (self.kmem_cache.name,
                                                int(self.gdb_obj.address), msg))
        self.error = True
        if misplaced:
            self.misplaced_error = msg
        else:
            print(msg)

    def __free_error(self, list_name: str) -> None:
        self.misplaced_list = list_name
        self.__error(": is on list %s, but has %d of %d objects allocated" %
                     (list_name, self.inuse, self.kmem_cache.objs_per_slab),
                     misplaced=True)

    def get_objects(self) -> Iterable[int]:
        bufsize = self.kmem_cache.buffer_size
        obj = self.s_mem
        # pylint: disable=unused-variable
        for i in range(self.kmem_cache.objs_per_slab):
            yield obj
            obj += bufsize

    def get_allocated_objects(self) -> Iterable[int]:
        for obj in self.get_objects():
            c = self.contains_obj(obj)
            if c[0]:
                yield obj

    def check(self, slabtype: int, nid: int) -> int:
        self.__populate_free()
        num_free = len(self.free)
        max_free = self.kmem_cache.objs_per_slab

        if self.kmem_cache.off_slab and not Slab.page_slab:
            struct_slab_slab = slab_from_obj_addr(int(self.gdb_obj.address))
            if not struct_slab_slab:
                self.__error(": OFF_SLAB struct slab is not a slab object itself")
            else:
                struct_slab_cache = struct_slab_slab.kmem_cache.name
                if not self.kmem_cache.off_slab_cache:
                    if struct_slab_cache != "size-64" and struct_slab_cache != "size-128":
                        self.__error(": OFF_SLAB struct slab is in a wrong cache %s" %
                                     struct_slab_cache)
                    else:
                        self.kmem_cache.off_slab_cache = struct_slab_cache
                elif struct_slab_cache != self.kmem_cache.off_slab_cache:
                    self.__error(": OFF_SLAB struct slab is in a wrong cache %s" %
                                 struct_slab_cache)

                struct_slab_obj = struct_slab_slab.contains_obj(self.gdb_obj.address)
                if not struct_slab_obj[0]:
                    self.__error(": OFF_SLAB struct slab is not allocated")
                    print(struct_slab_obj)
                elif struct_slab_obj[1] != int(self.gdb_obj.address):
                    self.__error(": OFF_SLAB struct slab at wrong offset{}"
                                 .format(int(self.gdb_obj.address) - struct_slab_obj[1]))

        if self.inuse + num_free != max_free:
            self.__error(": inuse=%d free=%d adds up to %d (should be %d)" %
                         (self.inuse, num_free,
                          self.inuse + num_free, max_free))

        if slabtype == slab_free:
            if num_free != max_free:
                self.__free_error("slab_free")
        elif slabtype == slab_partial:
            if num_free == 0 or num_free == max_free:
                self.__free_error("slab_partial")
        elif slabtype == slab_full:
            if num_free > 0:
                self.__free_error("slab_full")

        if self.page_slab:
            slab_nid = self.page.get_nid()
            if nid != slab_nid:
                self.__error(": slab is on nid %d instead of %d" %
                             (slab_nid, nid))
                print("free objects %d" % num_free)

        ac = self.kmem_cache.get_array_caches()
        last_page_addr = 0
        for obj in self.get_objects():
            if obj in self.free and obj in ac:
                self.__error(": obj %x is marked as free but in array cache:" % obj)
                print(ac[obj])
            try:
                page = page_from_addr(obj).compound_head()
            except gdb.NotAvailableError:
                self.__error(": failed to get page for object %x" % obj)
                continue

            if int(page.gdb_obj.address) == last_page_addr:
                continue

            last_page_addr = int(page.gdb_obj.address)

            if page.get_nid() != nid:
                self.__error(": obj %x is on nid %d instead of %d" %
                             (obj, page.get_nid(), nid))
            if not page.is_slab():
                self.__error(": obj %x is not on PageSlab page" % obj)
            kmem_cache_addr = int(page.get_slab_cache())
            if kmem_cache_addr != int(self.kmem_cache.gdb_obj.address):
                self.__error(": obj %x is on page where pointer to kmem_cache points to %x instead of %x" %
                             (obj, kmem_cache_addr,
                              int(self.kmem_cache.gdb_obj.address)))

            if self.page_slab:
                continue

            slab_addr = int(page.get_slab_page())
            if slab_addr != self.gdb_obj.address:
                self.__error(": obj %x is on page where pointer to slab wrongly points to %x" %
                             (obj, slab_addr))
        return num_free

class KmemCache:
    buffer_size_name = None
    nodelists_name = None
    percpu_name = None
    percpu_cache = None
    head_name = "list"
    alien_cache_type_exists = False

    @classmethod
    def check_kmem_cache_type(cls, gdbtype: gdb.Type) -> None:
        cls.buffer_size_name = find_member_variant(gdbtype, ['buffer_size', 'size'])
        cls.nodelists_name = find_member_variant(gdbtype, ['nodelists', 'node'])
        cls.percpu_name = find_member_variant(gdbtype, ['cpu_cache', 'array'])
        cls.percpu_cache = bool(cls.percpu_name == 'cpu_cache')
        cls.head_name = find_member_variant(gdbtype, ['next', 'list'])

    @classmethod
    # pylint: disable=unused-argument
    def setup_alien_cache_type(cls, gdbtype: gdb.Type) -> None:
        cls.alien_cache_type_exists = True

    def __init__(self, name: str, gdb_obj: gdb.Value) -> None:
        self.name = name
        self.gdb_obj = gdb_obj

        self.objs_per_slab = int(gdb_obj["num"])
        self.buffer_size = int(gdb_obj[KmemCache.buffer_size_name])

        if int(gdb_obj["flags"]) & 0x80000000:
            self.off_slab = True
            self.off_slab_cache: Optional[str]
            self.off_slab_cache = None
        else:
            self.off_slab = False

        self.array_caches: Dict[int, Dict] = dict()

    def __get_nodelist(self, node: int) -> gdb.Value:
        return self.gdb_obj[KmemCache.nodelists_name][node]

    def __get_nodelists(self) -> Iterable[Tuple[int, gdb.Value]]:
        for nid in for_each_nid():
            node = self.__get_nodelist(nid)
            if int(node) == 0:
                continue
            yield (nid, node.dereference())

    @staticmethod
    def all_find_obj(addr: int) -> Union[None, Tuple[bool, int,
                                                     Union[gdb.Value, None]]]:
        slab = slab_from_obj_addr(addr)
        if not slab:
            return None
        return slab.contains_obj(addr)

    def __fill_array_cache(self, acache: gdb.Value, ac_type: str,
                           nid_src: int, nid_tgt: int) -> None:
        avail = int(acache["avail"])

        # TODO check avail > limit
        if avail == 0:
            return

        cache_dict = {"ac_type" : ac_type,
                      "nid_src" : nid_src,
                      "nid_tgt" : nid_tgt}

#        print(cache_dict)
        if ac_type == AC_PERCPU:
            nid_tgt = numa_node_id(nid_tgt)

        for i in range(avail):
            ptr = int(acache["entry"][i])
#            print(hex(ptr))
            if ptr in self.array_caches:
                print(col_error("WARNING: array cache duplicity detected!"))
            else:
                self.array_caches[ptr] = cache_dict

            page = page_from_addr(ptr)
            obj_nid = page.get_nid()

            if obj_nid != nid_tgt:
                print(col_error("Object {:#x} in cache {} is on wrong nid {} instead of {}"
                                .format(ptr, cache_dict, obj_nid, nid_tgt)))

    def __fill_alien_caches(self, node: gdb.Value, nid_src: int) -> None:
        alien_cache = node["alien"]

        # TODO check that this only happens for single-node systems?
        if int(alien_cache) == 0:
            return

        for nid in for_each_nid():
            array = alien_cache[nid].dereference()

            # TODO: limit should prevent this?
            if array.address == 0:
                continue

            if self.alien_cache_type_exists:
                array = array["ac"]

            # A node cannot have alien cache on the same node, but some
            # kernels (xen) seem to have a non-null pointer there anyway
            if nid_src == nid:
                continue

            self.__fill_array_cache(array, AC_ALIEN, nid_src, nid)

    def __fill_percpu_caches(self) -> None:
        cpu_cache = self.gdb_obj[KmemCache.percpu_name]

        for cpu in for_each_online_cpu():
            if KmemCache.percpu_cache:
                array = get_percpu_var(cpu_cache, cpu)
            else:
                array = cpu_cache[cpu].dereference()

            self.__fill_array_cache(array, AC_PERCPU, -1, cpu)

    def __fill_all_array_caches(self) -> None:
        self.array_caches = dict()

        self.__fill_percpu_caches()

        # TODO check and report collisions
        for (nid, node) in self.__get_nodelists():
            shared_cache = node["shared"]
            if int(shared_cache) != 0:
                self.__fill_array_cache(shared_cache.dereference(), AC_SHARED, nid, nid)

            self.__fill_alien_caches(node, nid)

    def get_array_caches(self) -> Dict[int, Dict]:
        if not self.array_caches:
            self.__fill_all_array_caches()

        return self.array_caches

    def __get_allocated_objects(self, node: gdb.Value,
                                slabtype: int) -> Iterable[int]:
        for slab in self.get_slabs_of_type(node, slabtype):
            for obj in slab.get_allocated_objects():
                yield obj

    def get_allocated_objects(self) -> Iterable[int]:
        # pylint: disable=unused-variable
        for (nid, node) in self.__get_nodelists():
            for obj in self.__get_allocated_objects(node, slab_partial):
                yield obj
            for obj in self.__get_allocated_objects(node, slab_full):
                yield obj

    def get_slabs_of_type(self, node: gdb.Value, slabtype: int,
                          reverse: bool = False,
                          exact_cycles: bool = False) -> Iterable[Slab]:
        wrong_list_nodes = dict()
        for stype in range(3):
            if stype != slabtype:
                wrong_list_nodes[int(node[slab_list_fullname[stype]].address)] = stype

        slab_list = node[slab_list_fullname[slabtype]]
        for list_head in list_for_each(slab_list, reverse=reverse, exact_cycles=exact_cycles):
            try:
                if int(list_head) in wrong_list_nodes.keys():
                    wrong_type = wrong_list_nodes[int(list_head)]
                    print(col_error("Encountered head of {} slab list while traversing {} slab list, skipping"
                                    .format(slab_list_name[wrong_type],
                                            slab_list_name[slabtype])))
                    continue

                slab = Slab.from_list_head(list_head, self)
            except gdb.NotAvailableError:
                traceback.print_exc()
                print("failed to initialize slab object from list_head {:#x}: {}"
                      .format(int(list_head), sys.exc_info()[0]))
                continue
            yield slab


    def __check_slab(self, slab: Slab, slabtype: int, nid: int,
                     errors: Dict) -> int:
        addr = int(slab.gdb_obj.address)
        free = 0

        if slab.error is False:
            free = slab.check(slabtype, nid)

        if slab.misplaced_error is None and errors['num_misplaced'] > 0:
            if errors['num_misplaced'] > 0:
                print(col_error("{} slab objects were misplaced, printing the last:"
                                .format(errors['num_misplaced'])))
                print(errors['last_misplaced'])
                errors['num_misplaced'] = 0
                errors['last_misplaced'] = None

        if slab.error is False:
            errors['num_ok'] += 1
            errors['last_ok'] = addr
            if not errors['first_ok']:
                errors['first_ok'] = addr
        else:
            if errors['num_ok'] > 0:
                print("{} slab objects were ok between {:#x} and {:#x}"
                      .format(errors['num_ok'], errors['first_ok'], errors['last_ok']))
                errors['num_ok'] = 0
                errors['first_ok'] = None
                errors['last_ok'] = None

            if slab.misplaced_error is not None:
                if errors['num_misplaced'] == 0:
                    print(slab.misplaced_error)
                errors['num_misplaced'] += 1
                errors['last_misplaced'] = slab.misplaced_error

        return free

    def ___check_slabs(self, node: gdb.Value, slabtype: int, nid: int,
                       reverse: bool = False) -> Tuple[bool, int, int]:
        slabs = 0
        free = 0
        check_ok = True

        errors = {'first_ok': None,
                  'last_ok': None,
                  'num_ok': 0,
                  'first_misplaced': None,
                  'last_misplaced': None,
                  'num_misplaced': 0}

        try:
            for slab in self.get_slabs_of_type(node, slabtype, reverse,
                                               exact_cycles=True):
                try:
                    free += self.__check_slab(slab, slabtype, nid, errors)
                except gdb.NotAvailableError as e:
                    print(col_error("Exception when checking slab {:#x}:{}"
                                    .format(int(slab.gdb_obj.address), e)))
                    traceback.print_exc()
                slabs += 1

        except (gdb.NotAvailableError, ListError) as e:
            print(col_error("Unrecoverable error when traversing {} slab list: {}"
                            .format(slab_list_name[slabtype], e)))
            check_ok = False

        count = errors['num_ok']
        if count:
            print("{} slab objects were ok between {:#x} and {:#x}"
                  .format(errors['num_ok'], errors['first_ok'], errors['last_ok']))

        count = errors['num_misplaced']
        if count:
            print(col_error("{} slab objects were misplaced, printing the last:"
                            .format(errors['num_misplaced'])))
            print(errors['last_misplaced'])

        return (check_ok, slabs, free)

    def __check_slabs(self, node: gdb.Value, slabtype: int, nid: int) -> int:

        slab_list = node[slab_list_fullname[slabtype]]

        print("checking {} slab list {:#x}".format(slab_list_name[slabtype],
                                                   int(slab_list.address)))

        (check_ok, slabs, free) = self.___check_slabs(node, slabtype, nid)

        if not check_ok:
            print("Retrying the slab list in reverse order")
            (check_ok, slabs_rev, free_rev) = \
                self.___check_slabs(node, slabtype, nid, reverse=True)
            slabs += slabs_rev
            free += free_rev

        #print("checked {} slabs in {} slab list".format(
#                    slabs, slab_list_name[slabtype]))

        return free

    def check_array_caches(self) -> None:
        acs = self.get_array_caches()
        for ac_ptr in acs:
            ac_obj_slab = slab_from_obj_addr(ac_ptr)
            if not ac_obj_slab:
                print("cached pointer {:#x} in {} not found in slab"
                      .format(ac_ptr, acs[ac_ptr]))
            elif ac_obj_slab.kmem_cache.name != self.name:
                print("cached pointer {:#x} in {} belongs to wrong kmem cache {}"
                      .format(ac_ptr, acs[ac_ptr], ac_obj_slab.kmem_cache.name))
            else:
                ac_obj_obj = ac_obj_slab.contains_obj(ac_ptr)
                if ac_obj_obj[0] is False and ac_obj_obj[2] is None:
                    print("cached pointer {:#x} in {} is not allocated: {}".format(
                        ac_ptr, acs[ac_ptr], ac_obj_obj))
                elif ac_obj_obj[1] != ac_ptr:
                    print("cached pointer {:#x} in {} has wrong offset: ({}, {:#x}, {})"
                          .format(ac_ptr, acs[ac_ptr], ac_obj_obj[0],
                                  ac_obj_obj[1], ac_obj_obj[2]))

    def check_all(self) -> None:
        for (nid, node) in self.__get_nodelists():
            try:
                # This is version and architecture specific
                lock = int(node["list_lock"]["rlock"]["raw_lock"]["slock"])
                if lock != 0:
                    print(col_error("unexpected lock value in kmem_list3 {:#x}: {:#x}"
                                    .format(int(node.address), lock)))
            except gdb.error:
                print("Can't check lock state -- locking implementation unknown.")
            free_declared = int(node["free_objects"])
            free_counted = self.__check_slabs(node, slab_partial, nid)
            free_counted += self.__check_slabs(node, slab_full, nid)
            free_counted += self.__check_slabs(node, slab_free, nid)
            if free_declared != free_counted:
                print(col_error("free objects mismatch on node %d: declared=%d counted=%d" %
                                (nid, free_declared, free_counted)))
        self.check_array_caches()

class KmemCacheNotFound(RuntimeError):
    """The specified kmem_cache could not be found."""

kmem_caches: Dict[str, KmemCache] = dict()
kmem_caches_by_addr: Dict[int, KmemCache] = dict()

def setup_slab_caches(slab_caches: gdb.Symbol) -> None:
    list_caches = slab_caches.value()

    for cache in list_for_each_entry(list_caches,
                                     types.kmem_cache_type,
                                     KmemCache.head_name):
        name = cache["name"].string()
        kmem_cache = KmemCache(name, cache)

        kmem_caches[name] = kmem_cache
        kmem_caches_by_addr[int(cache.address)] = kmem_cache

def kmem_cache_from_addr(addr: int) -> KmemCache:
    try:
        return kmem_caches_by_addr[addr]
    except KeyError:
        raise KmemCacheNotFound(f"No kmem cache found for {addr}.")

def kmem_cache_from_name(name: str) -> KmemCache:
    try:
        return kmem_caches[name]
    except KeyError:
        raise KmemCacheNotFound(f"No kmem cache found for {name}.")

def kmem_cache_get_all() -> ValuesView[KmemCache]:
    return kmem_caches.values()

def slab_from_obj_addr(addr: int) -> Union[Slab, None]:
    page = page_from_addr(addr).compound_head()
    if not page.is_slab():
        return None

    return Slab.from_page(page)

type_cbs = TypeCallbacks([('struct page', Slab.check_page_type),
                          ('struct slab', Slab.check_slab_type),
                          ('kmem_bufctl_t', Slab.check_bufctl_type),
                          ('freelist_idx_t', Slab.check_bufctl_type),
                          ('struct kmem_cache',
                           KmemCache.check_kmem_cache_type),
                          ('struct alien_cache',
                           KmemCache.setup_alien_cache_type)])
symbol_cbs = SymbolCallbacks([('slab_caches', setup_slab_caches),
                              ('cache_chain', setup_slab_caches)])
