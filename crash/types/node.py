#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import gdb
from .util import container_of, find_member_variant, get_symbol_value
from .bitmap import for_each_set_bit
import crash.types.zone

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096

pgdat_type = gdb.lookup_type('pg_data_t')

class Node:

    nids_online = None
    nids_possible = None

    @staticmethod
    def __get_nodes_state(state):
        n_state = get_symbol_value(state)
        node_states = get_symbol_value("node_states")
        bits = node_states[n_state]["bits"]
        return list(for_each_set_bit(bits))

    @staticmethod
    def for_each_online_nid():
        if Node.nids_online is None:
            Node.nids_online = Node.__get_nodes_state("N_ONLINE")
        for nid in Node.nids_online:
            yield nid

    @staticmethod
    def for_each_online_node():
        for nid in Node.for_each_online_nid():
            yield Node.from_nid(nid)

    @staticmethod
    def for_each_nid():
        if Node.nids_possible is None:
            Node.nids_possible = Node.__get_nodes_state("N_POSSIBLE")
        for nid in Node.nids_possible:
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
            yield crash.types.zone.Zone(node_zones[zid], zid)

    def __init__(self, obj):
        self.gdb_obj = obj
