#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of, find_member_variant

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096L

struct_page_type = gdb.lookup_type('struct page')

vmemmap = gdb.Value(VMEMMAP_START).cast(struct_page_type.pointer())

def get_flag(flagname):
    return 1L << long(gdb.lookup_symbol("PG_" + flagname, None)[0].value())

PG_tail = get_flag("tail")
PG_slab = get_flag("slab")

class Page:
    slab_cache_name = find_member_variant(struct_page_type,
                                    ("slab_cache", "lru"))
    slab_page_name = find_member_variant(struct_page_type,
                                    ("slab_page", "lru"))

    @staticmethod
    def from_pfn(pfn):
        return Page(vmemmap[pfn])

    @staticmethod
    def from_addr(addr):
        return Page.from_pfn((addr - DIRECTMAP_START) / PAGE_SIZE)

    @staticmethod
    def from_page_addr(addr):
        page = gdb.Value(addr).cast(struct_page_type.pointer()).dereference()
        return Page(page)

    def is_tail(self):
        return bool(self.flags & PG_tail)

    def is_slab(self):
        return bool(self.flags & PG_slab)

    def get_slab_cache(self):
        if Page.slab_cache_name == "lru":
            return self.gdb_obj["lru"]["next"]
        return self.gdb_obj[Page.slab_cache_name]

    def get_slab_page(self):
        if Page.slab_page_name == "lru":
            return self.gdb_obj["lru"]["prev"]
        return self.gdb_obj[Page.slab_page_name]

    def compound_head(self):
        if not self.is_tail():
            return self

        first_page = long(self.gdb_obj["first_page"])
        return Page.from_page_addr(first_page)
        
    def __init__(self, obj):
        self.gdb_obj = obj
        self.flags = long(obj["flags"])
