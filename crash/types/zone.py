#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of, find_member_variant
from crash.types.node import Node

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096L

# TODO abstract away
nr_cpu_ids = long(gdb.lookup_global_symbol("nr_cpu_ids").value())
nr_node_ids = long(gdb.lookup_global_symbol("nr_node_ids").value())

zone_type = gdb.lookup_type('struct zone')

class Zone:

    @staticmethod
    def for_each():
        for node in Node.for_each_node():
            for zone in node.for_each_zone():
                yield zone

    def __init__(self, obj):
        self.gdb_obj = obj
