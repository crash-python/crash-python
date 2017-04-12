# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from .util import container_of
from .list import list_for_each_entry
import sys

if sys.version_info.major >= 3:
    long = int

klist_node_type = gdb.lookup_type("struct klist_node")
klist_type = gdb.lookup_type("struct klist")
def klist_for_each(klist):
    if klist.type == klist_type.pointer():
        klist = klist.dereference()
    elif klist.type != klist_type:
        raise gdb.GdbError("Must be struct klist not {}".format(klist.type))

    for node in list_for_each_entry(klist['k_list'], klist_node_type, 'n_node'):
        if node['n_klist'] != klist.address:
            raise Error("Corrupted")
        yield node

def klist_for_each_entry(klist, gdbtype, member):
    for node in klist_for_each(klist):
        if node.type != klist_node_type:
            raise TypeError("Type {} found. Expected {}.".format(node.type), klist_node_type)
        yield container_of(node, gdbtype, member)
