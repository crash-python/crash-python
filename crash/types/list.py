#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of

list_head_type = gdb.lookup_type("struct list_head")
def list_for_each(list_head):
    if list_head.type == list_head_type.pointer():
        list_head = list_head.dereference()
    elif list_head.type != list_head_type:
        raise gdb.GdbError("Must be struct list_head not %s" % list_head.type)

    node = list_head['next'].dereference()
    while node.address != list_head.address:
        yield node.address
        node = node['next'].dereference()

def list_for_each_entry(list_head, gdbtype, member):
    for node in list_for_each(list_head):
        if node.type != list_head_type.pointer():
            raise TypeError("Type %s found. Expected struct list_head *." % node.type)
        yield container_of(node, gdbtype, member)
