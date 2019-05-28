# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterator, Set

import gdb
from crash.util import container_of
from crash.util.symbols import Types
from crash.exceptions import ArgumentTypeError, UnexpectedGDBTypeError

class ListError(Exception):
    pass

class CorruptListError(ListError):
    pass

class ListCycleError(CorruptListError):
    pass

types = Types([ 'struct list_head' ])

def list_for_each(list_head: gdb.Value, include_head: bool=False,
                  reverse: bool=False, print_broken_links: bool=True,
                  exact_cycles: bool=False) -> Iterator[gdb.Value]:
    """
    Iterate over a list and yield each node

    Args:
        list_head (gdb.Value<struct list_head or struct list_head *>):
            The list to iterate
        include_head (bool, optional, default=False):
            Include the head of the list in iteration - useful
            for lists with no anchors
        reverse (bool, optional, default=False):
            Iterate the list in reverse order (follow the prev links)
        print_broken_links (bool, optional, default=True):
            Print warnings about broken links
        exact_cycles (bool, optional, default=False):
            Detect and raise an exception if a cycle is detected in the list

    Yields:
        gdb.Value<struct list_head>: The next node in the list

    Raises:
        CorruptListError: the list is corrupted
        ListCycleError: the list contains cycles
        BufferError: portions of the list cannot be read
    """
    pending_exception = None
    if not isinstance(list_head, gdb.Value):
        raise ArgumentTypeError('list_head', list_head, gdb.Value)
    if list_head.type == types.list_head_type.pointer():
        list_head = list_head.dereference()
    elif list_head.type != types.list_head_type:
        raise UnexpectedGDBTypeError('list_head', types.list_head_type,
                                     list_head.type)
    if list_head.type is not types.list_head_type:
        types.override('struct list_head', list_head.type)
    fast = None
    if int(list_head.address) == 0:
        raise CorruptListError("list_head is NULL pointer.")

    next_ = 'next'
    prev_ = 'prev'
    if reverse:
        next_ = 'prev'
        prev_ = 'next'

    if exact_cycles:
        visited: Set[int] = set()

    if include_head:
        yield list_head.address

    try:
        nxt = list_head[next_]
        prev = list_head
        if int(nxt) == 0:
            raise CorruptListError("{} pointer is NULL".format(next_))
        node = nxt.dereference()
    except gdb.error as e:
        raise BufferError("Failed to read list_head {:#x}: {}"
                          .format(int(list_head.address), str(e)))

    while node.address != list_head.address:
        if exact_cycles:
            if int(node.address) in visited:
                raise ListCycleError("Cycle in list detected.")
            else:
                visited.add(int(node.address))
        try:
            if int(prev.address) != int(node[prev_]):
                error = ("broken {} link {:#x} -{}-> {:#x} -{}-> {:#x}"
                         .format(prev_, int(prev.address), next_, int(node.address),
                                 prev_, int(node[prev_])))
                pending_exception = CorruptListError(error)
                if print_broken_links:
                    print(error)
                # broken prev link means there might be a cycle that
                # does not include the initial head, so start detecting
                # cycles
                if not exact_cycles and fast is not None:
                    fast = node
            nxt = node[next_]
            # only yield after trying to read something from the node, no
            # point in giving out bogus list elements
            yield node.address
        except gdb.error as e:
            raise BufferError("Failed to read list_head {:#x} in list {:#x}: {}"
                              .format(int(node.address), int(list_head.address), str(e)))

        try:
            if fast is not None:
                # are we detecting cycles? advance fast 2 times and compare
                # each with our current node (Floyd's Tortoise and Hare
                # algorithm)
                for i in range(2):
                    fast = fast[next_].dereference()
                    if node.address == fast.address:
                        raise ListCycleError("Cycle in list detected.")
        except gdb.error:
            # we hit an unreadable element, so just stop detecting cycles
            # and the slow iterator will hit it as well
            fast = None

        prev = node
        if int(nxt) == 0:
            raise CorruptListError("{} -> {} pointer is NULL"
                                   .format(node.address, next_))
        node = nxt.dereference()

    if pending_exception is not None:
        raise pending_exception

def list_for_each_entry(list_head: gdb.Value, gdbtype: gdb.Type,
                        member: str, include_head: bool=False,
                        reverse: bool=False, print_broken_links: bool=True,
                        exact_cycles: bool=False) -> Iterator[gdb.Value]:
    """
    Iterate over a list and yield each node's containing object

    Args:
        list_head (gdb.Value<struct list_head or struct list_head *>):
            The list to iterate
        gdbtype (gdb.Type): The type of the containing object
        member (str): The name of the member in the containing object that
            corresponds to the list_head
        include_head (bool, optional, default=False):
            Include the head of the list in iteration - useful for
            lists with no anchors
        reverse (bool, optional, default=False):
            Iterate the list in reverse order (follow the prev links)
        print_broken_links (bool, optional, default=True):
            Print warnings about broken links
        exact_cycles (bool, optional, default=False):
            Detect and raise an exception if a cycle is detected in the list

    Yields:
        gdb.Value<gdbtype>: The next node in the list
    """

    for node in list_for_each(list_head, include_head=include_head,
                              reverse=reverse,
                              print_broken_links=print_broken_links,
                              exact_cycles=exact_cycles):
        yield container_of(node, gdbtype, member)

def list_empty(list_head):
    addr = int(list_head.address)
    if list_head.type.code == gdb.TYPE_CODE_PTR:
        addr = int(list_head)

    return addr == int(list_head['next'])
