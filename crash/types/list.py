# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
from crash.util import container_of
from crash.infra import CrashBaseClass, export

if sys.version_info.major >= 3:
    long = int

class ListError(Exception):
    pass

class CorruptListError(ListError):
    pass

class ListCycleError(CorruptListError):
    pass

class TypesListClass(CrashBaseClass):
    __types__ = [ 'struct list_head' ]

    @export
    def list_for_each(self, list_head, include_head=False, reverse=False):
        pending_exception = None
        if isinstance(list_head, gdb.Symbol):
            list_head = list_head.value()
        if not isinstance(list_head, gdb.Value):
            raise TypeError("list_head must be gdb.Value representing 'struct list_head' or a 'struct list_head *' not {}"
                            .format(type(list_head).__name__))
        if list_head.type == self.list_head_type.pointer():
            list_head = list_head.dereference()
        elif list_head.type != self.list_head_type:
            raise TypeError("Must be struct list_head not {}"
                            .format(str(list_head.type)))
        fast = None
        if long(list_head.address) == 0:
            raise CorruptListError("list_head is NULL pointer.")

        next_ = 'next'
        prev_ = 'prev'
        if reverse:
            next_ = 'prev'
            prev_ = 'next'

        if include_head:
            yield list_head.address

        try:
            nxt = list_head[next_]
            prev = list_head
            if long(nxt) == 0:
                raise CorruptListError("{} pointer is NULL".format(next_))
            node = nxt.dereference()
        except gdb.error as e:
            raise BufferError("Failed to read list_head {:#x}: {}"
                              .format(long(list_head.address), str(e)))

        while node.address != list_head.address:
            yield node.address

            try:
                if long(prev.address) != long(node[prev_]):
                    error = ("broken {} link {:#x} -{}-> {:#x} -{}-> {:#x}"
                             .format(prev_, long(prev.address), next_, long(node.address),
                                     prev_, long(node[prev_])))
                    pending_exception = CorruptListError(error)
                    # broken prev link means there might be a cycle that
                    # does not include the initial head, so start detecting
                    # cycles
                    fast = node
                nxt = node[next_]

                if fast is not None:
                    # are we detecting cycles? advance fast 2 times and compare
                    # each with our current node (Floyd's Tortoise and Hare
                    # algorithm)
                    for i in range(2):
                        fast = fast[next_].dereference()
                        if node.address == fast.address:
                            raise ListCycleError("Cycle in list detected.")

                prev = node
                if long(nxt) == 0:
                    raise CorruptListError("{} pointer is NULL".format(next_))
                node = nxt.dereference()
            except gdb.error as e:
                raise BufferError("Failed to read list_head {:#x} in list {:#x}: {}"
                                  .format(long(node.address), long(list_head.address), str(e)))
        if pending_exception is not None:
            raise pending_exception

    @export
    def list_for_each_entry(self, list_head, gdbtype, member, include_head=False, reverse=False):
        for node in list_for_each(list_head, include_head=include_head, reverse=reverse):
            if node.type != self.list_head_type.pointer():
                raise TypeError("Type {} found. Expected struct list_head *."
                                .format(str(node.type)))
            yield container_of(node, gdbtype, member)
