#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
The crash.types.node module offers helpers to work with NUMA nodes.
"""

from typing import Iterable, List, Type, TypeVar

from crash.util.symbols import Symbols, Symvals, Types, SymbolCallbacks
from crash.types.percpu import get_percpu_var
from crash.types.bitmap import for_each_set_bit
from crash.exceptions import DelayedAttributeError
import crash.types.zone

import gdb

symbols = Symbols(['numa_node'])
symvals = Symvals(['numa_cpu_lookup_table', 'node_data'])
types = Types(['pg_data_t', 'struct zone'])

def numa_node_id(cpu: int) -> int:
    """
    Return the NUMA node ID for a given CPU

    Args:
        cpu: The CPU number to obtain the NUMA node ID
    Returns:
        :obj:`int`: The NUMA node ID for the specified CPU.
    """
    if gdb.current_target().arch.name() == "powerpc:common64":
        return int(symvals.numa_cpu_lookup_table[cpu])
    return int(get_percpu_var(symbols.numa_node, cpu))

NodeType = TypeVar('NodeType', bound='Node')

class Node(object):
    """
    A wrapper around the Linux kernel 'struct node' structure
    """
    @classmethod
    def from_nid(cls: Type[NodeType], nid: int) -> 'Node':
        """
        Obtain a Node using the NUMA Node ID (nid)

        Args:
            nid: The NUMA Node ID

        Returns:
            :obj:`~crash.types.Node`: the Node wrapper for the struct
            node for this NID
        """
        return cls(symvals.node_data[nid].dereference())

    def for_each_zone(self) -> Iterable[crash.types.zone.Zone]:
        """
        Iterate over each zone contained in this NUMA node

        Yields:
            :obj:`~crash.types.Zone`: The next Zone in this Node
        """
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

    def __init__(self, obj: gdb.Value) -> None:
        """
        Initialize a Node using the gdb.Value for the struct node

        Args:
            obj: The node for which to construct a wrapper.  The value must be
                of type ``struct node``.
        """
        self.gdb_obj = obj

class NodeStates(object):
    """
    A state holder for Node states.

    Attributes:
        nids_online (:obj:`list` of :obj:`int`): A list of the online node IDs.
        nids_possible (:obj:`list` of :obj:`int`): A list of the possible
            node IDs.
    """
    nids_online: List[int] = list()
    nids_possible: List[int] = list()

    @classmethod
    def setup_node_states(cls, node_states_sym: gdb.Symbol) -> None:
        """
        Detect names of node states and which nodes are possible
        and online.

        Meant to be used as a SymbolCallback.

        Args:
            node_states_sym: The ``node_states`` symbol.
        """

        node_states = node_states_sym.value()
        enum_node_states = gdb.lookup_type("enum node_states")

        N_POSSIBLE = enum_node_states["N_POSSIBLE"].enumval
        N_ONLINE = enum_node_states["N_ONLINE"].enumval

        bits = node_states[N_POSSIBLE]["bits"]
        cls.nids_possible = list(for_each_set_bit(bits))

        bits = node_states[N_ONLINE]["bits"]
        cls.nids_online = list(for_each_set_bit(bits))

    def for_each_nid(self) -> Iterable[int]:
        """
        Iterate over each NUMA Node ID

        Yields:
            :obj:`int`: The next NUMA Node ID
        """
        if not self.nids_possible:
            raise DelayedAttributeError('node_states')

        for nid in self.nids_possible:
            yield nid

    def for_each_online_nid(self) -> Iterable[int]:
        """
        Iterate over each online NUMA Node ID

        Yields:
            :obj:`int`: The next NUMA Node ID
        """
        if not self.nids_online:
            raise DelayedAttributeError('node_states')

        for nid in self.nids_online:
            yield nid

symbol_cbs = SymbolCallbacks([('node_states', NodeStates.setup_node_states)])

_state = NodeStates()

def for_each_nid() -> Iterable[int]:
    """
    Iterate over each NUMA Node ID

    Yields:
        :obj:`int`: The next NUMA Node ID
    """
    for nid in _state.for_each_nid():
        yield nid

def for_each_online_nid() -> Iterable[int]:
    """
    Iterate over each online NUMA Node ID

    Yields:
        :obj:`int`: The next NUMA Node ID
    """
    for nid in _state.for_each_online_nid():
        yield nid

def for_each_node() -> Iterable[Node]:
    """
    Iterate over each NUMA Node

    Yields:
        :obj:`int`: The next NUMA Node
    """
    for nid in for_each_nid():
        yield Node.from_nid(nid)

def for_each_online_node() -> Iterable[Node]:
    """
    Iterate over each Online NUMA Node

    Yields:
        :obj:`int`: The next NUMA Node
    """
    for nid in for_each_online_nid():
        yield Node.from_nid(nid)

def for_each_zone() -> Iterable[crash.types.zone.Zone]:
    for node in for_each_node():
        for zone in node.for_each_zone():
            yield zone

def for_each_populated_zone() -> Iterable[crash.types.zone.Zone]:
    #TODO: some filter thing?
    for zone in for_each_zone():
        if zone.is_populated():
            yield zone
