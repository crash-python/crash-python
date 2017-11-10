#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
import random

import gdb
from .util import container_of, find_member_variant
import sys

if sys.version_info.major >= 3:
    long = int

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096
NODES_SHIFT     = 10

struct_page_type = gdb.lookup_type('struct page')

vmemmap = gdb.Value(VMEMMAP_START).cast(struct_page_type.pointer())
# TODO works only on x86?
max_pfn = long(gdb.lookup_global_symbol("max_pfn").value())

def get_flag(flagname):
    sym = gdb.lookup_symbol("PG_" + flagname, None)[0]
    if sym is not None:
        return 1 << long(sym.value())
    else:
        return None

PG_tail = get_flag("tail")
PG_slab = get_flag("slab")

NR_FLAGS = long(gdb.lookup_symbol("__NR_PAGEFLAGS", None)[0].value())

pageflags_type = gdb.lookup_type("enum pageflags")

#TODO debuginfo won't tell us, depends on version?
PAGE_MAPPING_ANON = 1

class Page:
    slab_cache_name = find_member_variant(struct_page_type,
                                    ("slab_cache", "lru"))
    slab_page_name = find_member_variant(struct_page_type,
                                    ("slab_page", "lru"))

    @staticmethod
    def from_pfn(pfn):
        return Page(vmemmap[pfn], pfn)

    @staticmethod
    def from_addr(addr):
        return Page.from_pfn((addr - DIRECTMAP_START) / PAGE_SIZE)

    @staticmethod
    def from_page_addr(addr):
        page_ptr = gdb.Value(addr).cast(struct_page_type.pointer())
        pfn = (addr - VMEMMAP_START) / struct_page_type.sizeof
        return Page(page_ptr.dereference(), pfn)

    @staticmethod
    def from_obj(gdb_obj):
        pfn = (long(gdb_obj.address) - VMEMMAP_START) / struct_page_type.sizeof
        return Page(gdb_obj, pfn)

    @staticmethod
    def for_each():
        for pfn in range(max_pfn):
            try:
                yield Page.from_pfn(pfn)
            except gdb.error as e:
                # TODO: distinguish pfn_valid() and report failures for those?
                pass

    @staticmethod
    def for_random(count):
        for pfn in random.sample(xrange(max_pfn), count):
            try:
                yield Page.from_pfn(pfn)
            except gdb.error as e:
                # TODO: distinguish pfn_valid() and report failures for those?
                pass

    def is_tail(self):
        if PG_tail is not None:
            return bool(self.flags & PG_tail)
        else:
            return bool(self.gdb_obj["compound_head"] & 1)

    def is_slab(self):
        return bool(self.flags & PG_slab)

    def is_anon(self):
        mapping = long(self.gdb_obj["mapping"])
        return (mapping & PAGE_MAPPING_ANON) != 0

    def is_buddy(self):
        return int(self.gdb_obj["_mapcount"]["counter"]) == int(-128L)

    def is_buddy_tail(self):
        if self.get_count() != 0:
            return False

        # todo unhardcode
        for pfn in range(self.pfn, max(self.pfn - 1024, 0) -1):
            p = Page.from_pfn(pfn)

            if p.is_buddy():
                order = long(p.gdb_obj["private"])
                return self.pfn < p.pfn + 1 << order

            if p.get_count() != 0:
                return False

    def get_count(self):
        return int(self.compound_head().gdb_obj["_count"]["counter"])

    def get_slab_cache(self):
        if Page.slab_cache_name == "lru":
            return self.gdb_obj["lru"]["next"]
        return self.gdb_obj[Page.slab_cache_name]

    def get_slab_page(self):
        if Page.slab_page_name == "lru":
            return self.gdb_obj["lru"]["prev"]
        return self.gdb_obj[Page.slab_page_name]

    def get_nid(self):
        # TODO unhardcode
        return self.flags >> (64 - NODES_SHIFT)

    def get_flags(self):
        return self.flags & ((1 << NR_FLAGS) - 1)

    def print_flags(self):
        flags = self.get_flags()
        print ("%x" % flags)
        for field in pageflags_type.fields():
            if field.name == "__NR_PAGEFLAGS":
                break
            if self.flags & (1 << field.enumval):
                print(field.name)

    def compound_head(self):
        if not self.is_tail():
            return self

        if PG_tail is not None:
            first_page = long(self.gdb_obj["first_page"])
        else:
            first_page = long(self.gdb_obj["compound_head"]) - 1
        return Page.from_page_addr(first_page)

    def __init__(self, obj, pfn):
        self.gdb_obj = obj
        self.pfn = pfn
        self.flags = long(obj["flags"])
