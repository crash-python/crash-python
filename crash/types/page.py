#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of, find_member_variant

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096L
NODES_SHIFT     = 10

struct_page_type = gdb.lookup_type('struct page')

vmemmap = gdb.Value(VMEMMAP_START).cast(struct_page_type.pointer())

def get_flag(flagname):
    sym = gdb.lookup_symbol("PG_" + flagname, None)[0]
    if sym is not None:
        return 1L << long(sym.value())
    else:
        return None

PG_tail = get_flag("tail")
PG_slab = get_flag("slab")

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
        # TODO works only on x86?
        max_pfn = long(gdb.lookup_global_symbol("max_pfn").value())
        for pfn in range(max_pfn):
            try:
                yield Page.from_pfn(pfn)
            except gdb.error, e:
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
