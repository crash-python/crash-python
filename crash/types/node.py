#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.util import container_of, find_member_variant, get_symbol_value
from crash.types.percpu import get_percpu_var
from crash.types.bitmap import for_each_set_bit
import crash.types.zone

class TypesNodeUtilsClass(CrashBaseClass):
    __symbols__ = [ 'numa_node' ]
    __symvals__ = [ 'numa_cpu_lookup_table' ]

    @export
    def numa_node_id(self, cpu):
        if gdb.current_target().arch.name() == "powerpc:common64":
            return int(self.numa_cpu_lookup_table[cpu])
        else:
            return int(get_percpu_var(self.numa_node, cpu))

class Node(CrashBaseClass):
    __types__ = [ 'pg_data_t', 'struct zone' ]

    @staticmethod
    def from_nid(nid):
        node_data = gdb.lookup_global_symbol("node_data").value()
        return Node(node_data[nid].dereference())

    def for_each_zone(self):
        node_zones = self.gdb_obj["node_zones"]

        ptr = int(node_zones[0].address)

        (first, last) = node_zones.type.range()
        for zid in range(first, last + 1):
            # FIXME: gdb seems to lose the alignment padding with plain
            # node_zones[zid], so we have to simulate it using zone_type.sizeof
            # which appears to be correct
            zone = gdb.Value(ptr).cast(self.zone_type.pointer()).dereference()
            yield crash.types.zone.Zone(zone, zid)
            ptr += self.zone_type.sizeof

    def __init__(self, obj):
        self.gdb_obj = obj

class Nodes(CrashBaseClass):

    __symbol_callbacks__ = [ ('node_states', 'setup_node_states') ]

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

    @export
    def for_each_nid(cls):
        for nid in cls.nids_possible:
            yield nid

    @export
    def for_each_online_nid(cls):
        for nid in cls.nids_online:
            yield nid

    @export
    def for_each_node(cls):
        for nid in cls.for_each_nid():
            yield Node.from_nid(nid)

    @export
    def for_each_online_node(cls):
        for nid in cls.for_each_online_nid():
            yield Node.from_nid(nid)

