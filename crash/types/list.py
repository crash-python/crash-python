#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import gdb
from .util import container_of
import sys

if sys.version_info.major >= 3:
    long = int

list_head_type = gdb.lookup_type("struct list_head")
def list_for_each(list_head, reverse=False):
    if list_head.type == list_head_type.pointer():
        list_head = list_head.dereference()
    elif list_head.type != list_head_type:
        raise gdb.GdbError("Must be struct list_head not %s" % list_head.type)

    fast = None
    next_ = 'next'
    prev_ = 'prev'
    if reverse:
        next_ = 'prev'
        prev_ = 'next'

    try:
        nxt = list_head[next_]
        prev = list_head
        node = nxt.dereference()
    except gdb.error as e:
        print(("Failed to read list_head %x" % list_head.address, (nxt)))
        return

    while node.address != list_head.address:
        yield node.address

        try:
            if long(prev.address) != long(node[prev_]):
                print(("broken %s link %x -%s-> %x -%s-> %x" %
                        (prev_, prev.address, next_, node.address, prev_, long(node[prev_]))))
                # broken prev link means there might be a cycle that does not
                # include the initial head, so start detecting cycles
                fast = node
            nxt = node[next_]

            if fast is not None:
                # are we detecting cycles? advance fast 2 times and compare
                # each with our current node (Floyd's Tortoise and Hare
                # algorithm)
                for i in range(2):
                    fast = fast[next_].dereference()
                    if node.address == fast.address:
                        print("detected linked list cycle, aborting traversal")
                        return

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
