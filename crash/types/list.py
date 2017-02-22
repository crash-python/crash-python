#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from .util import container_of

list_head_type = gdb.lookup_type("struct list_head")
def list_for_each(list_head):
    if list_head.type == list_head_type.pointer():
        list_head = list_head.dereference()
    elif list_head.type != list_head_type:
        raise gdb.GdbError("Must be struct list_head not %s" % list_head.type)

    try:
        nxt = list_head['next']
        prev = list_head
        node = nxt.dereference()
    except gdb.error as e:
        print(("Failed to read list_head %x" % list_head.address, (nxt)))
        return

    while node.address != list_head.address:
        yield node.address

        try:
            if int(prev.address) != int(node['prev']):
                print(("broken prev link %x -next-> %x -prev-> %x" %
                        (prev.address, node.address, int(node['prev']))))
            nxt = node['next']
            prev = node
            node = nxt.dereference()
        except gdb.error as e:
            print(("Failed to read list_head %x" % node.address))
            return

def list_for_each_entry(list_head, gdbtype, member):
    for node in list_for_each(list_head):
        if node.type != list_head_type.pointer():
            raise TypeError("Type %s found. Expected struct list_head *." % node.type)
        yield container_of(node, gdbtype, member)
