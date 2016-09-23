#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of, find_member_variant
from crash.types.zone import Zone

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096L

# TODO abstract away
nr_cpu_ids = long(gdb.lookup_global_symbol("nr_cpu_ids").value())
nr_node_ids = long(gdb.lookup_global_symbol("nr_node_ids").value())

pgdat_type = gdb.lookup_type('pg_data_t')

class Node:

    @staticmethod
    def for_each_nid():
        # TODO: use real bitmap for online nodes
        for nid in range(nr_node_ids):
            yield nid

    @staticmethod
    def for_each_node():
        for nid in Node.for_each_nid():
            yield Node.from_nid(nid)

    @staticmethod
    def from_nid(nid):
        node_data = gdb.lookup_global_symbol("node_data").value()
        return Node(node_data[nid].dereference())

    def for_each_zone(self):
        node_zones = self.gdb_obj["node_zones"]
        (first, last) = node_zones.type.range()
        for zid in range(first, last + 1):
            yield Zone(node_zones[zid])

    def __init__(self, obj):
        self.gdb_obj = obj
