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

    fast = None

    try:
        nxt = list_head['next']
        prev = list_head
        node = nxt.dereference()
    except gdb.error, e:
        print ("Failed to read list_head %x" % list_head.address, (nxt))
        return

    while node.address != list_head.address:
        yield node.address

        try:
            if long(prev.address) != long(node['prev']):
                print ("broken prev link %x -next-> %x -prev-> %x" %
                        (prev.address, node.address, long(node['prev'])))
                # broken prev link means there might be a cycle that does not
                # include the initial head, so start detecting cycles
                fast = node
            nxt = node['next']

            if fast is not None:
                # are we detecting cycles? advance fast 2 times and compare
                # each with our current node (Floyd's Tortoise and Hare
                # algorithm)
                for i in range(2):
                    fast = fast['next'].dereference()
                    if node.address == fast.address:
                        print ("detected linked list cycle, aborting traversal")
                        return

            prev = node
            node = nxt.dereference()
        except gdb.error, e:
            print ("Failed to read list_head %x" % node.address)
            return

def list_for_each_entry(list_head, gdbtype, member):
    for node in list_for_each(list_head):
        if node.type != list_head_type.pointer():
            raise TypeError("Type %s found. Expected struct list_head *." % node.type)
        yield container_of(node, gdbtype, member)
