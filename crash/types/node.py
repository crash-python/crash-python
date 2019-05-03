#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.util.symbols import Symbols, Symvals, Types, SymbolCallbacks
from crash.util import container_of, find_member_variant, get_symbol_value
from crash.types.percpu import get_percpu_var
from crash.types.bitmap import for_each_set_bit
import crash.types.zone

symbols = Symbols([ 'numa_node' ])
symvals = Symvals([ 'numa_cpu_lookup_table', 'node_data' ])
types = Types([ 'pg_data_t', 'struct zone' ])

def numa_node_id(cpu):
    if gdb.current_target().arch.name() == "powerpc:common64":
        return int(symvals.numa_cpu_lookup_table[cpu])
    else:
        return int(get_percpu_var(symbols.numa_node, cpu))

class Node(object):
    @staticmethod
    def from_nid(nid):
        return Node(symvals.node_data[nid].dereference())

    def for_each_zone(self):
        node_zones = self.gdb_obj["node_zones"]

        ptr = int(node_zones[0].address)

        (first, last) = node_zones.type.range()
        for zid in range(first, last + 1):
            # FIXME: gdb seems to lose the alignment padding with plain
            # node_zones[zid], so we have to simulate it using zone_type.sizeof
            # which appears to be correct
            zone = gdb.Value(ptr).cast(types.zone_type.pointer()).dereference()
            yield crash.types.zone.Zone(zone, zid)
            ptr += types.zone_type.sizeof

    def __init__(self, obj):
        self.gdb_obj = obj

class NodeStates(object):
    nids_online = None
    nids_possible = None

    @classmethod
    def setup_node_states(cls, node_states_sym):

        node_states = node_states_sym.value()
        enum_node_states = gdb.lookup_type("enum node_states")

        N_POSSIBLE = enum_node_states["N_POSSIBLE"].enumval
        N_ONLINE = enum_node_states["N_ONLINE"].enumval

        bits = node_states[N_POSSIBLE]["bits"]
        cls.nids_possible = list(for_each_set_bit(bits))

        bits = node_states[N_ONLINE]["bits"]
        cls.nids_online = list(for_each_set_bit(bits))

symbol_cbs = SymbolCallbacks([('node_states', NodeStates.setup_node_states)])

def for_each_nid():
    for nid in NodeStates.nids_possible:
        yield nid

def for_each_online_nid():
    for nid in NodeStates.nids_online:
        yield nid

def for_each_node():
    for nid in for_each_nid():
        yield Node.from_nid(nid)

def for_each_online_node():
    for nid in for_each_online_nid():
        yield Node.from_nid(nid)

