#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from abc import ABC, abstractmethod

from typing import TypeVar, Union, Tuple, Iterable, Dict, Optional, Set, List,\
                   cast
from typing import ValuesView

import sys
import traceback

import gdb

from crash.util import container_of, find_member_variant,\
                       safe_find_member_variant
from crash.util.symbols import Types, TypeCallbacks, SymbolCallbacks
from crash.types.percpu import get_percpu_var
from crash.types.list import list_for_each, list_for_each_entry, ListError
from crash.types.page import page_from_gdb_obj, page_from_addr, Page, page_addr,\
                             for_each_page_flag
from crash.types.node import for_each_nid
from crash.types.cpu import for_each_online_cpu
from crash.types.node import numa_node_id

# TODO: put in utils
def print_flags(val: int, names: Dict[str, int]) -> str:
    first = True
    ret = f"0x{val:x}"
    for name, flag in names.items():
        if val & flag != 0:
            prefix = " (" if first else "|"
            ret += f"{prefix}{name}"
            first = False
    if not first:
        ret += ")"
    return ret

def col_error(msg: str) -> str:
    return f"\033[1;31;40m {msg}\033[0;37;40m "

def col_bold(msg: str) -> str:
    return f"\033[1;37;40m {msg}\033[0;37;40m "

# TODO: put to separate type
def atomic_long_read(val: gdb.Value) -> int:
    return int(val["counter"])

types = Types(['kmem_cache', 'struct kmem_cache', 'struct page', 'void *'])

SlabType = TypeVar('SlabType', bound='Slab')
KmemCacheType = TypeVar('KmemCacheType', bound='KmemCache')

ArrayCacheEntry = Dict[str, Union[int, str]]

class ProcessingFlags:

    def __init__(self, print_level: int = 0):
        self.print_level = print_level

class Slab(ABC):
    """
    A common superclass representing a slab, i.e. a collection of objects on a
    single (possibly high-order) page.

    Args:
        gdb_obj: The structure to wrap, of type ``struct slab`` or
            ``struct page``.
        kmem_cache: The kmem_cache instance the slab belongs to.

    Attributes:
        gdb_obj (:obj:`gdb.Value`): The structure being wrapped. The value
            is of type ``struct slab`` or ``struct page``.
        address (:obj:`int`): Address of the structure being wrapped.
        kmem_cache (:obj:`KmemCache`): The cache the slab belongs to.
        free (:obj:`Set[int]`): Set of addresses of free objects in the slab.
        nr_objects (:obj:`int): Total number of objects in the slab.
        nr_inuse (:obj:`int): Number of allocated objects in the slab.
        nr_free (:obj:`int): Number of free objects in the slab.
    """

    def __init__(self, gdb_obj: gdb.Value, kmem_cache: 'KmemCache') -> None:
        self.gdb_obj = gdb_obj
        self.address = int(gdb_obj.address)
        self.kmem_cache = kmem_cache
        self.free: Set[int] = set()

        self._free_populated = False
        self.error = False
        self._misplaced_error = ""

    @classmethod
    @abstractmethod
    def from_page(cls, page: Page) -> 'Slab':
        """
        Create Slab object wrapper from a ``Page`` struct page wrapper.
        """

    @classmethod
    @abstractmethod
    def from_list_head(cls, list_head: gdb.Value,
                       kmem_cache: 'KmemCache') -> 'Slab':
        """
        Create Slab oject wrapper from a :obj:`gdb.Value` object of
        ``struct list_head`` type.
        """

    @abstractmethod
    def find_obj(self, addr: int) -> Optional[int]:
        """
        Returns starting address of object in slab.

        Args:
            addr: Address of the object to find.

        Returns:
            :obj:`int`: Starting address of the object, or None if the address
                does not fall into the slab's range. Note that while object
                address might be returned, addr might still be outside of valid
                range. Use contains_obj() to verify.
        """

    @abstractmethod
    def contains_obj(self, addr: int) -> Tuple[bool, int, Optional[str]]:
        """
        Returns whether the slab contains an object at given address.

        Args:
            addr: Address of object to check.

        Returns:
            :obj:`(contains, address, description)`: A tuple with object information.
            contains (:obj:`bool`): Whether addr points inside valid object
                range.
            address (:obj:`int`): Starting address of the object. Might be
                returned even if contains is False, when addr falls e.g. into a
                red zone or padding of an object.
            description (:obj:`str`): Optional description of where addr points
                to in case it's not a valid object.
        """

    @abstractmethod
    def obj_in_use(self, addr: int) -> Tuple[bool, Optional[str]]:
        """
        Returns information about whether object is allocated (in use) or free.

        Arg:
            addr: Base address of object to check, obtained e.g. by find.obj()

        Returns:
            :obj:`(in_use, free_details): A tuple with information.
            in_use (:obj:`bool`): Whether object is currently in use.
            free_details (:obj:`str`): If an object is in some special cache
                of free objects (e.g. per-cpu), a short description of such
                cache.
        """

    @abstractmethod
    def get_allocated_objects(self) -> Iterable[int]:
        """
        Generates object addresses for all allocated objects in the slab.
        """

    @abstractmethod
    def short_header(self) -> str:
        """
        Return a short header consisting of slab's address and role.
        """

    @abstractmethod
    def long_header(self) -> str:
        """
        Return a long header consisting of slab's address, role and stats.
        """

    @abstractmethod
    def print_objects(self) -> None:
        """
        Print all objects in slab, indicating if they are free or allocated.
        """

    @abstractmethod
    def _do_populate_free(self) -> None:
        """ Populate the set of free objects """

    def populate_free(self) -> None:
        """ Make sure the set of free objects is populated """
        if self._free_populated:
            return
        self._do_populate_free()
        self._free_populated = True

    def _pr_err(self, msg: str) -> None:
        msg = col_error(f"cache {self.kmem_cache.name} slab "
                        f"0x{self.address:x}{msg}")
        self.error = True
        print(msg)

class SlabSLAB(Slab):

    slab_list_head: str = 'list'
    page_slab: bool = False
    bufctl_type: gdb.Type
    real_slab_type: gdb.Type

    slab_partial = 0
    slab_full = 1
    slab_free = 2

    AC_PERCPU = "percpu"
    AC_SHARED = "shared"
    AC_ALIEN = "alien"

    BUFCTL_END = ~0 & 0xffffffff

    kmem_cache: 'KmemCacheSLAB'

    def __init__(self, gdb_obj: gdb.Value, kmem_cache: 'KmemCacheSLAB',
                 error: bool = False) -> None:
        super().__init__(gdb_obj, kmem_cache)
        if not isinstance(kmem_cache, KmemCacheSLAB):
            raise TypeError("kmem_cache must be of type KmemCacheSLAB")
        # FIXME: this doesn't seem to help
        self.kmem_cache = cast(KmemCacheSLAB, kmem_cache)
        self.error = error
        self.misplaced_list: Optional[str]
        self.misplaced_error: Optional[str]

        self.misplaced_list = None
        self.misplaced_error = None

        if error:
            return

        self.nr_objects = kmem_cache.objs_per_slab
        if self.page_slab:
            self.nr_inuse = int(gdb_obj["active"])
            self.page = page_from_gdb_obj(gdb_obj)
        else:
            self.nr_inuse = int(gdb_obj["inuse"])
        self.nr_free = self.nr_objects - self.nr_inuse
        self.s_mem = int(gdb_obj["s_mem"])

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
                  kmem_cache: Union[int, 'KmemCacheSLAB']) -> 'SlabSLAB':
        if not isinstance(kmem_cache, KmemCacheSLAB):
            kmem_cache = cast(KmemCacheSLAB, kmem_cache_from_addr(kmem_cache))
        slab_struct = gdb.Value(slab_addr).cast(cls.real_slab_type.pointer()).dereference()
        return cls(slab_struct, kmem_cache)

    @classmethod
    def from_page(cls, page: Page) -> 'SlabSLAB':
        kmem_cache_addr = int(page.get_slab_cache())
        kmem_cache = cast(KmemCacheSLAB, kmem_cache_from_addr(kmem_cache_addr))
        if kmem_cache is None:
            raise RuntimeError("No kmem cache found for page")
        if cls.page_slab:
            return cls(page.gdb_obj, kmem_cache)
        slab_addr = int(page.get_slab_page())
        return cls.from_addr(slab_addr, kmem_cache)

    @classmethod
    def from_list_head(cls, list_head: gdb.Value,
                       kmem_cache: 'KmemCache') -> 'SlabSLAB':
        gdb_obj = container_of(list_head, cls.real_slab_type, cls.slab_list_head)
        kmem_cache = cast(KmemCacheSLAB, kmem_cache)
        return cls(gdb_obj, kmem_cache)

    def short_header(self) -> str:
        return f"0x{self.address:x}"

    def long_header(self) -> str:
        return f"0x{self.address:x}"

    def print_objects(self) -> None:
        #TODO implement
        pass

    # pylint: disable=arguments-differ
    def _pr_err(self, msg: str, misplaced: bool = False) -> None:
        msg = col_error(f"cache {self.kmem_cache.name} slab "
                        f"0x{self.address:x}{msg}")
        self.error = True
        if misplaced:
            self.misplaced_error = msg
        else:
            print(msg)

    def __add_free_obj_by_idx(self, idx: int) -> bool:
        bufsize = self.kmem_cache.buffer_size

        if idx >= self.nr_objects:
            self._pr_err(f": free object index {idx} overflows {self.nr_objects}")
            return False

        obj_addr = self.s_mem + idx * bufsize
        if obj_addr in self.free:
            self._pr_err(f": object 0x{obj_addr:x} duplicated on freelist")
            return False

        self.free.add(obj_addr)
        return True

    def _do_populate_free(self) -> None:
        if self.page_slab:
            page = self.gdb_obj
            freelist = page["freelist"].cast(self.bufctl_type.pointer())
            for i in range(self.nr_inuse, self.nr_objects):
                obj_idx = int(freelist[i])
                self.__add_free_obj_by_idx(obj_idx)
            # XXX not generally useful and reliable
            if False and self.nr_objects > 1:
                all_zeroes = True
                for i in range(self.nr_objects):
                    obj_idx = int(freelist[i])
                    if obj_idx != 0:
                        all_zeroes = False
                if all_zeroes:
                    self._pr_err(": freelist full of zeroes")

        else:
            bufctl = self.gdb_obj.address[1].cast(self.bufctl_type).address
            f = int(self.gdb_obj["free"])
            while f != self.BUFCTL_END:
                if not self.__add_free_obj_by_idx(f):
                    self._pr_err(": bufctl cycle detected")
                    break

                f = int(bufctl[f])

    def find_obj(self, addr: int) -> Optional[int]:

        bufsize = self.kmem_cache.buffer_size

        if int(addr) < self.s_mem:
            return None

        idx = (int(addr) - self.s_mem) // bufsize
        if idx >= self.nr_objects:
            return None

        return int(self.s_mem + (idx * bufsize))

    def contains_obj(self, addr: int) -> Tuple[bool, int, Optional[str]]:
        obj_addr = self.find_obj(addr)

        if not obj_addr:
            return (False, 0, "address outside of valid object range")

        return (True, obj_addr, None)

    def obj_in_use(self, addr: int) -> Tuple[bool, Optional[str]]:

        self.populate_free()
        if addr in self.free:
            return (False, None)

        array_caches = self.kmem_cache.get_array_caches()

        if addr in array_caches:
            ac = array_caches[addr]

            ac_type = ac['ac_type'] # pylint: disable=unsubscriptable-object
            nid_tgt = int(ac['nid_tgt']) # pylint: disable=unsubscriptable-object
            if ac_type == self.AC_PERCPU:
                ac_desc = f"cpu {nid_tgt} cache"
            elif ac_type == self.AC_SHARED:
                ac_desc = f"shared cache on node {nid_tgt}"
            elif ac_type == self.AC_ALIEN:
                nid_src = int(ac['nid_src']) # pylint: disable=unsubscriptable-object
                ac_desc = f"alien cache on node {nid_src} for node {nid_tgt}"
            else:
                ac_desc = "unknown cache"

            return (False, ac_desc)

        return (True, None)

    def __free_error(self, list_name: str) -> None:
        self.misplaced_list = list_name
        self._pr_err(f": is on list {list_name}, but has {self.nr_inuse} of "
                     f"{self.nr_objects} objects allocated", misplaced=True)

    def get_objects(self) -> Iterable[int]:
        bufsize = self.kmem_cache.buffer_size
        obj = self.s_mem
        # pylint: disable=unused-variable
        for i in range(self.nr_objects):
            yield obj
            obj += bufsize

    def get_allocated_objects(self) -> Iterable[int]:
        for obj in self.get_objects():
            (in_use, _) = self.obj_in_use(obj)
            if in_use:
                yield obj

    def check(self, slabtype: int, nid: int) -> int:
        self.populate_free()
        num_free = len(self.free)
        max_free = self.nr_objects

        if self.kmem_cache.off_slab and not SlabSLAB.page_slab:
            struct_slab_slab = slab_from_obj_addr(self.address)
            if not struct_slab_slab:
                self._pr_err(": OFF_SLAB struct slab is not a slab object itself")
            else:
                struct_slab_cache = struct_slab_slab.kmem_cache.name
                if not self.kmem_cache.off_slab_cache:
                    if struct_slab_cache not in ("size-64", "size-128"):
                        self._pr_err(f": OFF_SLAB struct slab is in a wrong "
                                     f"cache {struct_slab_cache}")
                    else:
                        self.kmem_cache.off_slab_cache = struct_slab_cache
                elif struct_slab_cache != self.kmem_cache.off_slab_cache:
                    self._pr_err(f": OFF_SLAB struct slab is in a wrong cache "
                                 f"{struct_slab_cache}")

                addr = self.address
                struct_slab_obj = struct_slab_slab.contains_obj(addr)
                if not struct_slab_obj[0]:
                    self._pr_err(": OFF_SLAB struct slab is not allocated")
                    print(struct_slab_obj)
                elif struct_slab_obj[1] != addr:
                    off = addr - struct_slab_obj[1]
                    self._pr_err(f": OFF_SLAB struct slab at wrong offset {off}")

        if self.nr_inuse + num_free != max_free:
            self._pr_err(f": inuse={self.nr_inuse} free={num_free} adds up to "
                         f"{self.nr_inuse + num_free} (should be {max_free})")

        if slabtype == self.slab_free:
            if num_free != max_free:
                self.__free_error("slab_free")
        elif slabtype == self.slab_partial:
            if num_free in (0, max_free):
                self.__free_error("slab_partial")
        elif slabtype == self.slab_full:
            if num_free > 0:
                self.__free_error("slab_full")

        if self.page_slab:
            slab_nid = self.page.get_nid()
            if nid != slab_nid:
                self._pr_err(f": slab is on nid {slab_nid} instead of {nid}")
                print(f"free objects {num_free}")

        ac = self.kmem_cache.get_array_caches()
        last_page_addr = 0
        for obj in self.get_objects():
            if obj in self.free and obj in ac:
                self._pr_err(f": obj 0x{obj:x} is marked as free but in array cache:")
                print(ac[obj])
            try:
                page = page_from_addr(obj).compound_head()
            except gdb.NotAvailableError:
                self._pr_err(f": failed to get page for object 0x{obj:x}")
                continue

            if page.address == last_page_addr:
                continue

            last_page_addr = page.address

            if page.get_nid() != nid:
                self._pr_err(f": obj 0x{obj:x} is on nid {page.get_nid()} instead of {nid}")
            if not page.is_slab():
                self._pr_err(f": obj 0x{obj:x} is not on PageSlab page")
            kmem_cache_addr = int(page.get_slab_cache())
            if kmem_cache_addr != self.kmem_cache.address:
                self._pr_err(f": obj 0x{obj:x} is on page where pointer to kmem_cache "
                             f"points to 0x{kmem_cache_addr:x} instead of "
                             f"0x{self.kmem_cache.address:x}")

            if self.page_slab:
                continue

            slab_addr = int(page.get_slab_page())
            if slab_addr != self.address:
                self._pr_err(f": obj 0x{obj:x} is on page where pointer to slab "
                             f"wrongly points to 0x{slab_addr:x}")
        return num_free

class SlabSLUB(Slab):

    kmem_cache: 'KmemCacheSLUB'

    def __init__(self, gdb_obj: gdb.Value, kmem_cache: 'KmemCacheSLUB') -> None:
        super().__init__(gdb_obj, kmem_cache)
        self.nr_objects = int(gdb_obj["objects"])
        self.nr_inuse = int(gdb_obj["inuse"])
        self.nr_free = self.nr_objects - self.nr_inuse
        self.base_address = page_addr(int(gdb_obj.address))

    def slab_role(self) -> str:
        self.kmem_cache.slub_process_once()
        addr = self.address
        if addr in self.kmem_cache.cpu_slabs:
            return self.kmem_cache.cpu_slabs[addr]
        if addr in self.kmem_cache.node_slabs:
            return self.kmem_cache.node_slabs[addr]
        if self.nr_free == 0:
            return "untracked full"
        return "unknown"

    def short_header(self) -> str:
        return f"0x{self.address:x} ({self.slab_role()})"

    def long_header(self) -> str:
        return (f"0x{self.address:x} ({self.slab_role()}) objects {self.nr_objects} "
                f"active {self.nr_inuse} free {self.nr_free} base addr "
                f"0x{self.base_address:x}")

    def _do_populate_free(self) -> None:
        cpu_freelists = self.kmem_cache.cpu_freelists

        self.free = set()
        fp_offset = self.kmem_cache.fp_offset

        page = self.gdb_obj
        freelist = page["freelist"]
        nr_free = 0

        while freelist != 0:
            nr_free += 1
            if nr_free > self.nr_objects:
                self._pr_err(":too many objects on freelist, aborting traversal")
                break

            #TODO validate the pointers - check_valid_pointer()
            obj_addr = int(freelist)
            self.free.add(obj_addr)
            freelist += fp_offset
            freelist = freelist.cast(types.void_p_type.pointer()).dereference()
            if obj_addr in cpu_freelists:
                self._pr_err(f": free object 0x{obj_addr:x} found cached in "
                             f"{cpu_freelists[obj_addr]}")

        if len(self.free) != self.nr_free:
            self._pr_err(f": nr_free={self.nr_free} but freelist has "
                         f"{len(self.free)} entries")

    def find_obj(self, addr: int) -> Optional[int]:

        page = self.gdb_obj
        base = page_addr(int(page.address))

        if addr < base:
            return None

        nr_objects = int(page["objects"])

        idx = (addr - base) // self.kmem_cache.size

        if idx >= nr_objects:
            return None

        obj_addr = base + self.kmem_cache.red_left_pad() + idx * self.kmem_cache.size

        return obj_addr

    def contains_obj(self, addr: int) -> Tuple[bool, int, Optional[str]]:

        obj_addr = self.find_obj(addr)

        if not obj_addr:
            return (False, 0, "address outside of valid object range")

        if addr < obj_addr:
            return (False, obj_addr, "address inside left red zone padding")

        if addr > obj_addr + self.kmem_cache.inuse:
            # TODO perhaps distinguish which metadata
            return (False, obj_addr, "address inside metadata behind object")

        return (True, obj_addr, None)

    def obj_in_use(self, addr: int) -> Tuple[bool, Optional[str]]:

        self.kmem_cache.slub_process_once()
        self.populate_free()

        if addr in self.free:
            return (False, None)

        if addr in self.kmem_cache.cpu_freelists:
            return (False, self.kmem_cache.cpu_freelists[addr])

        return (True, None)

    def get_objects(self) -> Iterable[int]:
        page = self.gdb_obj
        base = page_addr(int(page.address)) + self.kmem_cache.red_left_pad()
        slot_size = self.kmem_cache.size

        nr_objects = int(page["objects"])
        for idx in range(nr_objects):
            obj_addr = base + idx * slot_size
            yield obj_addr

    def get_allocated_objects(self) -> Iterable[int]:
        for obj in self.get_objects():
            (in_use, _) = self.obj_in_use(obj)
            if in_use:
                yield obj

    def print_objects(self) -> None:
        self.populate_free()
        print("  FREE / [ALLOCATED]")
        for obj in self.get_objects():
            free = False
            free_where = ""
            if obj in self.free:
                free = True
            if obj in self.kmem_cache.cpu_freelists:
                free = True
                free_where = f"  ({self.kmem_cache.cpu_freelists[obj]})"
            if free:
                print(f"  0x{obj:x}{free_where}")
            else:
                print(f" [0x{obj:x}]")


    def warn_frozen(self, expected: int, header: str) -> None:
        warning = "not frozen but should be" if expected else "frozen but shouldn't be"
        if expected != self.gdb_obj["frozen"]:
            self._pr_err(f"({header}) {warning}")

    @classmethod
    def from_list_head(cls, list_head: gdb.Value,
                       kmem_cache: 'KmemCache') -> 'SlabSLUB':
        gdb_obj = container_of(list_head, types.page_type, 'lru')
        kmem_cache = cast(KmemCacheSLUB, kmem_cache)
        return cls(gdb_obj, kmem_cache)

    @classmethod
    def from_page_obj(cls, page: gdb.Value) -> 'SlabSLUB':
        if page.type.code == gdb.TYPE_CODE_PTR:
            page = page.dereference()
        kmem_cache_addr = int(page["slab_cache"])
        kmem_cache = kmem_cache_from_addr(kmem_cache_addr)
        if kmem_cache is None:
            raise RuntimeError("No kmem cache found for page")
        kmem_cache = cast(KmemCacheSLUB, kmem_cache)
        return cls(page, kmem_cache)

    @classmethod
    def from_page(cls, page: Page) -> 'SlabSLUB':
        return cls.from_page_obj(page.gdb_obj)

SLAB_RED_ZONE = 0x00000400

class KmemCache(ABC):
    buffer_size_name = None
    nodelists_name = None
    percpu_name = None
    percpu_cache = None
    head_name = "list"
    alien_cache_type_exists = False
    SLUB = False
    slub_debug_compiled = True

    SlabFlags = {
        'CONSISTENCY_CHECKS' : 0x00000100,
        'RED_ZONE'           : 0x00000400,
        'POISON'             : 0x00000800,
        'HWCACHE_ALIGN'      : 0x00002000,
        'CACHE_DMA'          : 0x00004000,
        'STORE_USER'         : 0x00010000,
        'RECLAIM_ACCOUNT'    : 0x00020000,
        'PANIC'              : 0x00040000,
        'TYPESAFE_BY_RCU'    : 0x00080000,
        'MEM_SPREAD'         : 0x00100000,
        'TRACE'              : 0x00200000,
        'DEBUG_OBJECTS'      : 0x00400000,
        'NOLEAKTRACE'        : 0x00800000,
        'NOTRACK'            : 0x01000000,
        'FAILSLAB'           : 0x02000000,
        'ACCOUNT'            : 0x04000000,
    }

    def __init__(self, name: str, gdb_obj: gdb.Value) -> None:
        self.name = name
        self.gdb_obj = gdb_obj
        self.address = int(gdb_obj.address)

        self.size = int(gdb_obj["size"])
        self.object_size = int(gdb_obj["object_size"])
        self.flags = int(gdb_obj["flags"])

        self.objs_per_slab = 0

        self.array_caches: Dict[int, Dict] = dict()

    @classmethod
    def check_kmem_cache_type(cls, gdbtype: gdb.Type) -> None:
        cls.percpu_name = find_member_variant(gdbtype, ['cpu_cache', 'cpu_slab', 'array'])
        if cls.percpu_name == 'cpu_slab':
            cls.SLUB = True
        else:
            cls.buffer_size_name = find_member_variant(gdbtype, ['buffer_size', 'size'])
            cls.percpu_cache = bool(cls.percpu_name == 'cpu_cache')
            cls.head_name = find_member_variant(gdbtype, ['next', 'list'])
        cls.nodelists_name = find_member_variant(gdbtype, ['nodelists', 'node'])

    @classmethod
    def check_kmem_cache_node_type(cls, gdbtype: gdb.Type) -> None:
        nr_slabs_name = safe_find_member_variant(gdbtype, ['nr_slabs'])
        if nr_slabs_name is not None:
            cls.slub_debug_compiled = True

    @classmethod
    def create(cls, name: str, gdb_obj: gdb.Value) -> 'KmemCache':
        if cls.SLUB:
            return KmemCacheSLUB(name, gdb_obj)
        return KmemCacheSLAB(name, gdb_obj)

    @abstractmethod
    def list_all(self, verbosity: int) -> None:
        pass

    @abstractmethod
    def check_all(self) -> None:
        pass

    @abstractmethod
    def get_allocated_objects(self) -> Iterable[int]:
        pass

    def has_flag(self, flag_name: str) -> bool:
        flag = self.SlabFlags[flag_name]
        return self.flags & flag != 0

    def tracks_full_slabs(self) -> bool:
        return self.has_flag("STORE_USER")

    def _get_nodelist(self, node: int) -> gdb.Value:
        return self.gdb_obj[KmemCache.nodelists_name][node]

    def _get_nodelists(self) -> Iterable[Tuple[int, gdb.Value]]:
        for nid in for_each_nid():
            node = self._get_nodelist(nid)
            if int(node) == 0:
                continue
            yield (nid, node.dereference())

    def _pr_err(self, msg: str) -> None:
        msg = col_error(f"cache {self.name}{msg}")
        print(msg)

class KmemCacheSLAB(KmemCache):

    slab_list_name = {0: "partial", 1: "full", 2: "free"}
    slab_list_fullname = {0: "slabs_partial", 1: "slabs_full", 2: "slabs_free"}
    buffer_size: int

    def __init__(self, name: str, gdb_obj: gdb.Value) -> None:
        super().__init__(name, gdb_obj)
        self.objs_per_slab = int(gdb_obj["num"])
        self.buffer_size = int(gdb_obj[KmemCache.buffer_size_name])

        if int(gdb_obj["flags"]) & 0x80000000:
            self.off_slab = True
            self.off_slab_cache: Optional[str]
            self.off_slab_cache = None
        else:
            self.off_slab = False

    @classmethod
    # pylint: disable=unused-argument
    def setup_alien_cache_type(cls, gdbtype: gdb.Type) -> None:
        cls.alien_cache_type_exists = True

    def list_all(self, verbosity: int) -> None:
        print("Not yet implemented for SLAB")

    def check_all(self) -> None:
        nr_slabs = 0
        nr_objs = 0
        nr_free = 0

        for (nid, node) in self._get_nodelists():
#            try:
#                # This is version and architecture specific
#                lock = int(node["list_lock"]["rlock"]["raw_lock"]["slock"])
#                if lock != 0:
#                    print(col_error("unexpected lock value in kmem_list3 {:#x}: {:#x}"
#                                    .format(int(node.address), lock)))
#            except gdb.error:
#                print("Can't check lock state -- locking implementation unknown.")

            free_declared = int(node["free_objects"])
            free_counted = self.__check_slabs(node, SlabSLAB.slab_partial, nid)
            free_counted += self.__check_slabs(node, SlabSLAB.slab_full, nid)
            free_counted += self.__check_slabs(node, SlabSLAB.slab_free, nid)

            if free_declared != free_counted:
                self._pr_err(f": free objects mismatch on node {nid}: "
                             f"declared={free_declared} counted={free_counted}")
            self.check_array_caches()

            print(f"Node {nid}: nr_slabs={nr_slabs}, nr_objs={nr_objs}, nr_free={nr_free}")

    def get_allocated_objects(self) -> Iterable[int]:
        for (_, node) in self._get_nodelists():
            for obj in self.__get_allocated_objects(node, SlabSLAB.slab_partial):
                yield obj
            for obj in self.__get_allocated_objects(node, SlabSLAB.slab_full):
                yield obj

    def __fill_array_cache(self, acache: gdb.Value, ac_type: str,
                           nid_src: int, nid_tgt: int) -> None:
        avail = int(acache["avail"])

        # TODO check avail > limit
        if avail == 0:
            return

        cache_dict = {"ac_type" : ac_type,
                      "nid_src" : nid_src,
                      "nid_tgt" : nid_tgt}

        if ac_type == SlabSLAB.AC_PERCPU:
            nid_tgt = numa_node_id(nid_tgt)

        for i in range(avail):
            ptr = int(acache["entry"][i])
            if ptr in self.array_caches:
                self._pr_err(f": object 0x{ptr:x} is in cache {cache_dict} "
                             f"but also {self.array_caches[ptr]}")
            else:
                self.array_caches[ptr] = cache_dict

            page = page_from_addr(ptr)
            obj_nid = page.get_nid()

            if obj_nid != nid_tgt:
                self._pr_err(f": object 0x{ptr:x} in cache {cache_dict} is "
                             f"on wrong nid {obj_nid} instead of {nid_tgt}")

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

            self.__fill_array_cache(array, SlabSLAB.AC_ALIEN, nid_src, nid)

    def __fill_percpu_caches(self) -> None:
        cpu_cache = self.gdb_obj[KmemCache.percpu_name]

        for cpu in for_each_online_cpu():
            if KmemCache.percpu_cache:
                array = get_percpu_var(cpu_cache, cpu)
            else:
                array = cpu_cache[cpu].dereference()

            self.__fill_array_cache(array, SlabSLAB.AC_PERCPU, -1, cpu)

    def __fill_all_array_caches(self) -> None:
        self.array_caches = dict()

        self.__fill_percpu_caches()

        # TODO check and report collisions
        for (nid, node) in self._get_nodelists():
            shared_cache = node["shared"]
            if int(shared_cache) != 0:
                self.__fill_array_cache(shared_cache.dereference(),\
                    SlabSLAB.AC_SHARED, nid, nid)

            self.__fill_alien_caches(node, nid)

    def get_array_caches(self) -> Dict[int, ArrayCacheEntry]:
        if not self.array_caches:
            self.__fill_all_array_caches()

        return self.array_caches

    def get_slabs_of_type(self, node: gdb.Value, slabtype: int,
                          reverse: bool = False,
                          exact_cycles: bool = False) -> Iterable[SlabSLAB]:
        wrong_list_nodes = dict()
        for stype in range(3):
            if stype != slabtype:
                wrong_list_nodes[int(node[self.slab_list_fullname[stype]].address)] = stype

        slab_list = node[self.slab_list_fullname[slabtype]]
        for list_head in list_for_each(slab_list, reverse=reverse, exact_cycles=exact_cycles):
            addr = int(list_head.address)
            try:
                if addr in wrong_list_nodes.keys():
                    wrong_type = wrong_list_nodes[addr]
                    self._pr_err(f": encountered head of {self.slab_list_name[wrong_type]} "
                                 f"slab list while traversing {self.slab_list_name[slabtype]} "
                                 f"slab list, skipping")
                    continue

                slab = SlabSLAB.from_list_head(list_head, self)
            except gdb.NotAvailableError:
                traceback.print_exc()
                self._pr_err(f": failed to initialize slab object from list_head "
                             f"0x{addr:x}: {sys.exc_info()[0]}")
                continue
            yield slab

    def __get_allocated_objects(self, node: gdb.Value,
                                slabtype: int) -> Iterable[int]:
        for slab in self.get_slabs_of_type(node, slabtype):
            for obj in slab.get_allocated_objects():
                yield obj

    def __check_slab(self, slab: SlabSLAB, slabtype: int, nid: int,
                     errors: Dict) -> int:
        addr = slab.address
        free = 0

        if slab.error is False:
            free = slab.check(slabtype, nid)

        if slab.misplaced_error is None and errors['num_misplaced'] > 0:
            if errors['num_misplaced'] > 0:
                print(col_error(f"{errors['num_misplaced']} slab objects "
                                f"were misplaced, printing the last:"))
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
                print(f"{errors['num_ok']} slab objects were ok between "
                      f"0x{errors['first_ok']:x} and 0x{errors['last_ok']:x}")
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
                    self._pr_err(f": exception when checking slab "
                                 f"0x{slab.address:x}: {e}")
                    traceback.print_exc()
                slabs += 1

        except (gdb.NotAvailableError, ListError) as e:
            self._pr_err(f": unrecoverable error when traversing "
                         f"{self.slab_list_name[slabtype]} slab list: {e}")
            check_ok = False

        count = errors['num_ok']
        if (count and errors['first_ok'] is not None and
                errors['last_ok'] is not None):
            print(f"{errors['num_ok']} slab objects were ok between "
                  f"0x{errors['first_ok']:x} and 0x{errors['last_ok']:x}")

        count = errors['num_misplaced']
        if count:
            print(col_error(f"{errors['num_misplaced']} slab objects were "
                            f"misplaced, printing the last:"))
            print(errors['last_misplaced'])

        return (check_ok, slabs, free)

    def __check_slabs(self, node: gdb.Value, slabtype: int, nid: int) -> int:

        slab_list = node[self.slab_list_fullname[slabtype]]

        print(f"checking {self.slab_list_name[slabtype]} slab list "
              f"0x{int(slab_list.address):x}")

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
                self._pr_err(f": cached pointer 0x{ac_ptr:x} in 0x{acs[ac_ptr]:x} "
                             f"not found in any slab")
            elif ac_obj_slab.kmem_cache.address != self.address:
                self._pr_err(f": cached pointer 0x{ac_ptr:x} in 0x{acs[ac_ptr]:x} "
                             f"belongs to wrong kmem cache {ac_obj_slab.kmem_cache.name}")
            else:
                ac_obj_obj = ac_obj_slab.contains_obj(ac_ptr)
                if ac_obj_obj[0] is False and ac_obj_obj[2] is None:
                    self._pr_err(f": cached pointer 0x{ac_ptr:x} in 0x{acs[ac_ptr]:x} "
                                 f"is not allocated: {ac_obj_obj}")
                elif ac_obj_obj[1] != ac_ptr:
                    self._pr_err(f": cached pointer 0x{ac_ptr:x} in 0x{acs[ac_ptr]:x} "
                                 f"has wrong offset: ({ac_obj_obj[0]}, 0x{ac_obj_obj[1]:x}, "
                                 f"{ac_obj_obj[2]})")

class KmemCacheSLUB(KmemCache):

    __slub_full_slabs_scanned = False

    @classmethod
    def __slub_find_full_slabs(cls) -> None:

        if cls.__slub_full_slabs_scanned:
            return

        print("Searching for SLUB pages...")

        for page in for_each_page_flag(Page.PG_slab):
            if page.is_tail():
                continue

            if page.gdb_obj["inuse"] < page.gdb_obj["objects"]:
                continue

            cache_ptr = int(page.get_slab_cache())
            cache = kmem_cache_from_addr(cache_ptr)
            if not isinstance(cache, KmemCacheSLUB):
                raise TypeError(f"expected KmemCacheSLUB, got {type(cache)}")
            nid = page.get_nid()
            cache.full_slabs[nid].add(page.address)

        print("Searching for SLUB pages done!")
        cls.__slub_full_slabs_scanned = True

    def __init__(self, name: str, gdb_obj: gdb.Value) -> None:
        super().__init__(name, gdb_obj)
        self.fp_offset = int(gdb_obj["offset"])
        self.flags = int(gdb_obj["flags"])
        self._red_left_pad = int(gdb_obj["red_left_pad"])
        self.inuse = int(gdb_obj["inuse"])
        self.full_slabs: List[Set[int]] = [set() for x in for_each_nid()]
        self.cpu_slabs: Dict[int, str] = dict()
        self.node_slabs: Dict[int, str] = dict()
        self.cpu_slabs_objects = 0
        self.cpu_slabs_free = 0
        self.cpu_freelists: Dict[int, str] = dict()
        self.cpu_freelists_sizes: List[int] = [0 for x in for_each_online_cpu()]
        self.processed = False

    def list_all(self, verbosity: int) -> None:
        flags = ProcessingFlags(print_level=verbosity)
        self.process_all(flags)

    def check_all(self) -> None:
        flags = ProcessingFlags(print_level=1)
        self.process_all(flags)

    def get_allocated_objects(self) -> Iterable[int]:
        # TODO this is incomplete!
        for (_, node) in self._get_nodelists():
            partial_list = node["partial"]
            for list_head in list_for_each(partial_list):
                slub = SlabSLUB.from_list_head(list_head, self)
                for obj in slub.get_allocated_objects():
                    yield obj

    def red_left_pad(self) -> int:
        if self.flags & SLAB_RED_ZONE != 0:
            return self._red_left_pad
        return 0

    def _add_percpu_slub(self, slub: SlabSLUB, addr: int, _type: str) -> None:
        if addr in self.cpu_slabs:
            self._pr_err(f": slab page 0x{addr:x} is both a {_type} and {self.cpu_slabs[addr]}")
        else:
            self.cpu_slabs[addr] = _type
            self.cpu_slabs_objects += slub.nr_objects
            self.cpu_slabs_free += slub.nr_free
            # TODO warn if full/free?
            slub.populate_free()

    def _populate_cpu_freelist(self, cpu_slab: gdb.Value, cache_type: str) -> int:

        fp_offset = self.fp_offset

        freelist = cpu_slab["freelist"]
        if freelist != 0:
            nr_objects = int(cpu_slab["page"]["objects"])
        nr_free = 0

        # unlike page.freelist (void *), kmem_cache_cpu is (void **)
        # this messes with the += fp_offset arithmetic, so recast it
        freelist = freelist.cast(types.void_p_type)
        while freelist != 0:
            nr_free += 1
            if nr_free > nr_objects:
                self._pr_err(f" has too many objects on {cache_type}, aborting traversal")
                break

            #TODO validate the pointers - check_valid_pointer()
            obj_addr = int(freelist)
            if obj_addr in self.cpu_freelists:
                self._pr_err(f" per-cpu freelist duplicitydetected: object "
                             f"0x{obj_addr:x} is in {cache_type} and also "
                             f"{self.cpu_freelists[obj_addr]}")
            else:
                self.cpu_freelists[obj_addr] = cache_type
            freelist += fp_offset

            freelist = freelist.cast(types.void_p_type.pointer()).dereference()

        return nr_free

    def _process_percpu(self, flags: ProcessingFlags) -> None:
        fill_cpu_slabs = bool(len(self.cpu_slabs) == 0)

        if not fill_cpu_slabs and flags.print_level == 0:
            # nothing to do
            return

        cpu_slab_var = self.gdb_obj["cpu_slab"]
        for cpu in for_each_online_cpu():
            cpu_slab = get_percpu_var(cpu_slab_var, cpu)

            if fill_cpu_slabs:
                nr_freelist = self._populate_cpu_freelist(cpu_slab, f"CPU {cpu} freelist")
                self.cpu_freelists_sizes[cpu] = nr_freelist
            else:
                nr_freelist = self.cpu_freelists_sizes[cpu]

            if flags.print_level >= 2:
                print(f"CPU {cpu} kmem_cache_cpu 0x{int(cpu_slab.address):x}, "
                      f"freelist has {nr_freelist} cached objects")

            slab_addr = int(cpu_slab["page"])
            if slab_addr == 0:
                if flags.print_level >= 2:
                    print(f"CPU {cpu} slab: (none)")
            else:
                slab = SlabSLUB.from_page_obj(cpu_slab["page"])
                if fill_cpu_slabs:
                    self._add_percpu_slub(slab, slab_addr, f"CPU {cpu} slab")
                if flags.print_level >= 2:
                    print(f"CPU {cpu} slab: {slab.long_header()}")
                slab.warn_frozen(1, f"CPU {cpu}")
                if flags.print_level >= 4:
                    slab.print_objects()

            partial = cpu_slab["partial"]
            if int(partial) == 0:
                if flags.print_level >= 2:
                    print(f"CPU {cpu} partial: (empty)")
            else:
                if flags.print_level >= 3:
                    print(f"CPU {cpu} partial:")

                # pages should grow down by 1, last in partial list should have 1
                pages_expected = int(partial["pages"])
                pages = -1

                nr_partial = 0
                nr_objects = 0
                nr_active = 0

                while int(partial) != 0:
                    nr_partial += 1
                    slab = SlabSLUB.from_page_obj(partial)
                    if fill_cpu_slabs:
                        self._add_percpu_slub(slab, int(partial), f"CPU {cpu} partial")
                    pages = int(partial["pages"])
                    if flags.print_level >= 3:
                        print(f"  {slab.long_header()}")
                        if flags.print_level >= 4:
                            slab.print_objects()
                    slab.warn_frozen(1, f"CPU {cpu} partial")
                    nr_objects += slab.nr_objects
                    nr_active += slab.nr_inuse
                    if pages != pages_expected:
                        self._pr_err(f" CPU {cpu} partial 0x{int(partial):x} "
                                     f"pages={pages} expected {pages_expected}")
                    pages_expected = pages - 1
                    partial = partial["next"]
                if pages != 1:
                    self._pr_err(f"CPU {cpu} last partial 0x{int(partial):x} "
                                 f"pages field is {pages} and not 1")
                if flags.print_level >= 2:
                    print(f"CPU {cpu} partial: Slabs: {nr_partial} Objects: total "
                          f"{nr_objects} active {nr_active} free {nr_objects - nr_active}")

    def process_all(self, flags: ProcessingFlags) -> None:

        if flags.print_level == 0 and self.processed:
            # nothing to do
            return

        if flags.print_level >= 2:
            # TODO slab sizes (kmem_cache.oo etc)
            cache_flags = print_flags(self.flags, self.SlabFlags)
            print(f"Cache {self.name} at 0x{self.address:x} objsize "
                  f"{self.object_size} ({self.size}) flags {cache_flags}")

        self._process_percpu(flags)
        nr_slabs = 0
        nr_partial = 0
        nr_objs = 0
        nr_free_objs = self.cpu_slabs_free + len(self.cpu_freelists)
        nr_full_list = 0

        for (nid, node) in self._get_nodelists():
            if self.slub_debug_compiled:
                node_nr_slabs = atomic_long_read(node["nr_slabs"])
                node_nr_objs = atomic_long_read(node["total_objects"])
                nr_slabs += node_nr_slabs
                nr_objs += node_nr_objs

            nr_partial_expected = int(node["nr_partial"])
            nr_partial += nr_partial_expected
            partial_list = node["partial"]
            node_nr_partial = 0

            if flags.print_level >= 2:
                print(f"Node {nid} Slabs: total {node_nr_slabs} partial "
                      f"{nr_partial_expected} Objects: total {node_nr_objs}")

            # TODO check if slab page is on proper node (also full slabs)
            for list_head in list_for_each(partial_list):
                node_nr_partial += 1
                slub = SlabSLUB.from_list_head(list_head, self)
                if flags.print_level >= 3:
                    print(f"Partial slab {slub.long_header()}")
                    if flags.print_level >= 4:
                        slub.print_objects()
                slub.warn_frozen(0, f"Node {nid} partial")
                if not self.processed:
                    self.node_slabs[slub.address] = f"Node {nid} partial"
                nr_free_objs += slub.nr_free

                if flags.print_level >= 4:
                    slub.print_objects()
            if nr_partial_expected != node_nr_partial:
                self._pr_err(f" node {nid} partial list has {node_nr_partial} "
                             f"pages but expected {nr_partial_expected}")

            if self.slub_debug_compiled:
                nr_full_list_node = 0
                for list_head in list_for_each(node["full"]):
                    nr_full_list_node += 1
                    slub = SlabSLUB.from_list_head(list_head, self)
                    if flags.print_level >= 3:
                        print(f"Full slab {slub.long_header()}")
                        if flags.print_level >= 4:
                            slub.print_objects()
                    slub.warn_frozen(0, f"Node {nid} full")
                    if not self.processed:
                        self.node_slabs[slub.address] = f"Node {nid} full"
                    # TODO warn if not actually full
                if nr_full_list_node > 0 and not self.tracks_full_slabs():
                    self._pr_err(f" node {nid} full list not empty ({nr_full_list_node} slabs) "
                                 f"although SLAB_STORE_USER not enabled")
                nr_full_list += nr_full_list_node

        nr_percpu = len(self.cpu_slabs)
        nr_full = nr_slabs - nr_partial - nr_percpu
        if self.tracks_full_slabs() and nr_full_list != nr_full:
            self._pr_err(f": expected to find {nr_full} slabs on full lists, "
                         f"but found {nr_full_list}")
        if flags.print_level == 1:
            cache_flags = print_flags(self.flags, self.SlabFlags)
            print(f"Cache {self.name} at 0x{self.address:x} objsize "
                  f"{self.object_size} ({self.size}) Slabs: total {nr_slabs} partial "
                  f"{nr_partial} percpu {nr_percpu} full {nr_full} "
                  f"Objects: total {nr_objs} active {nr_objs - nr_free_objs} "
                  f"free {nr_free_objs} Flags: {cache_flags}")

        elif flags.print_level >= 2:
            print(f"Cache {self.name} total: Slabs: total {nr_slabs} partial "
                  f"{nr_partial} percpu {nr_percpu} full {nr_full} "
                  f"Objects: total {nr_objs} active {nr_objs - nr_free_objs} "
                  f"free {nr_free_objs}")

        self.processed = True

    def slub_process_once(self) -> None:
        if not self.processed:
            self.process_all(ProcessingFlags())

class KmemCacheNotFound(RuntimeError):
    """The specified kmem_cache could not be found."""

__kmem_caches: Dict[str, KmemCache] = dict()
__kmem_caches_by_addr: Dict[int, KmemCache] = dict()

def __setup_slab_caches(slab_caches: gdb.Symbol) -> None:
    list_caches = slab_caches.value()

    for cache in list_for_each_entry(list_caches,
                                     types.kmem_cache_type,
                                     KmemCache.head_name):
        name = cache["name"].string()
        kmem_cache = KmemCache.create(name, cache)

        __kmem_caches[name] = kmem_cache
        __kmem_caches_by_addr[int(cache.address)] = kmem_cache

# TODO: move the following functions to subsystem/ ?
def kmem_cache_from_addr(addr: int) -> KmemCache:
    try:
        return __kmem_caches_by_addr[addr]
    except KeyError:
        raise KmemCacheNotFound(f"No kmem cache found for {addr}.") from None

def kmem_cache_from_name(name: str) -> KmemCache:
    try:
        return __kmem_caches[name]
    except KeyError:
        raise KmemCacheNotFound(f"No kmem cache found for {name}.") from None

def kmem_cache_get_all() -> ValuesView[KmemCache]:
    return __kmem_caches.values()

def slab_from_page(page: Page) -> Slab:
    if KmemCache.SLUB:
        return SlabSLUB.from_page(page)
    return SlabSLAB.from_page(page)

def slab_from_obj_addr(addr: int) -> Optional[Slab]:
    page = page_from_addr(addr).compound_head()
    if not page.is_slab():
        return None

    return slab_from_page(page)

type_cbs = TypeCallbacks([('struct page', SlabSLAB.check_page_type),
                          ('struct slab', SlabSLAB.check_slab_type),
                          ('kmem_bufctl_t', SlabSLAB.check_bufctl_type),
                          ('freelist_idx_t', SlabSLAB.check_bufctl_type),
                          ('struct kmem_cache',
                           KmemCache.check_kmem_cache_type),
                          ('struct kmem_cache_node',
                           KmemCache.check_kmem_cache_node_type),
                          ('struct alien_cache',
                           KmemCacheSLAB.setup_alien_cache_type)])
symbol_cbs = SymbolCallbacks([('slab_caches', __setup_slab_caches),
                              ('cache_chain', __setup_slab_caches)])
