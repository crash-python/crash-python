# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable

import gdb
from crash.util import container_of
from crash.types.list import list_for_each_entry
from crash.exceptions import CorruptedError, InvalidArgumentError

from crash.util.symbols import Types

types = Types([ 'struct klist_node', 'struct klist' ])

class KlistCorruptedError(CorruptedError):
    pass

def klist_for_each(klist: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterate over a klist and yield each node

    Args:
        klist: The list to iterate.  The value must be of type
            ``struct klist`` or ``struct klist *``.

    Yields:
        :obj:`gdb.Value`: The next node in the list.  The value is of type
            ``struct klist_node``.
    """
    if klist.type == types.klist_type.pointer():
        klist = klist.dereference()
    elif klist.type != types.klist_type:
        raise InvalidArgumentError("klist must be gdb.Value representing 'struct klist' or 'struct klist *' not {}"
                        .format(klist.type))
    if klist.type is not types.klist_type:
        types.override('struct klist', klist.type)

    for node in list_for_each_entry(klist['k_list'],
                                    types.klist_node_type, 'n_node'):
        if node['n_klist'] != klist.address:
            raise KlistCorruptedError("Corrupted")
        yield node

def klist_for_each_entry(klist: gdb.Value, gdbtype: gdb.Type,
                         member: str) -> gdb.Value:
    """
    Iterate over a klist and yield each node's containing object

    Args:
        klist: The list to iterate.  The value must be of type
            ``struct klist`` or ``struct klist *``.
        gdbtype: The type of the containing object
        member: The name of the member in the containing object that
            corresponds to the klist_node

    Yields:
        :obj:`gdb.Value`: The next node in the list.  The value is of the
        specified type.
    """
    for node in klist_for_each(klist):
        if node.type is not types.klist_node_type:
            types.override('struct klist_node', node.type)
        yield container_of(node, gdbtype, member)
