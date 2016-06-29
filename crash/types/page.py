#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of

VMEMMAP_START = 0xffffea0000000000
PAGE_SIZE = 4096L

struct_page_type = gdb.lookup_type('struct page')

vmemmap = gdb.Value(VMEMMAP_START).cast(struct_page_type.pointer())

class Page:

    gdb_obj = None

    @staticmethod
    def from_pfn(pfn):
        return Page(vmemmap[pfn])

    @staticmethod
    def from_addr(addr):
        return Page.from_pfn(addr / PAGE_SIZE)

    def __init__(self, obj):
        self.gdb_obj = obj
