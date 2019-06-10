# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterator, Set

from crash.util import container_of
from crash.util.symbols import Types
from crash.exceptions import ArgumentTypeError, UnexpectedGDBTypeError

import gdb

class ListError(Exception):
    pass

class CorruptListError(ListError):
    pass

class ListCycleError(CorruptListError):
    pass

types = Types(['struct list_head'])

def list_for_each(list_head: gdb.Value, include_head: bool = False,
                  reverse: bool = False, print_broken_links: bool = True,
                  exact_cycles: bool = False) -> Iterator[gdb.Value]:
    """
    Iterate over a list and yield each node

    Args:
        list_head: The list to iterate.  The value must be of type
            ``struct list_head`` or ``struct list_head *``.
        include_head (optional): Include the head of the list in
            iteration - useful for lists with no anchors
        reverse (optional): Iterate the list in reverse order
            (follow the ``prev`` links)
        print_broken_links (optional): Print warnings about broken links
        exact_cycles (optional): Detect and raise an exception if
            a cycle is detected in the list

    Yields:
        gdb.Value: The next node in the list.  The value is
        of type ``struct list_head``.

    Raises:
        :obj:`.CorruptListError`: the list is corrupted
        :obj:`.ListCycleError`: the list contains cycles
        :obj:`BufferError`: portions of the list cannot be read
        :obj:`gdb.NotAvailableError`: The target value is not available.
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
            visited.add(int(node.address))
        try:
            if int(prev.address) != int(node[prev_]):
                error = f"broken {prev_} link {int(prev.address):#x} "
                error += f"-{next_}-> {int(node.address):#x} "
                error += f"-{prev_}-> {int(node[prev_]):#x}"
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
                for i in range(2): # pylint: disable=unused-variable
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
        # The pylint error seems to think we'll raise None here
        raise pending_exception # pylint: disable=raising-bad-type

def list_for_each_entry(list_head: gdb.Value, gdbtype: gdb.Type,
                        member: str, include_head: bool = False,
                        reverse: bool = False, print_broken_links: bool = True,
                        exact_cycles: bool = False) -> Iterator[gdb.Value]:
    """
    Iterate over a list and yield each node's containing object

    Args:
        list_head: The list to iterate.  The value must be of type
            ``struct list_head`` or ``struct list_head *``.
        gdbtype: The type of the containing object
        member: The name of the member in the containing object that
            corresponds to the list_head
        include_head (optional):
            Include the head of the list in iteration - useful for
            lists with no anchors
        reverse (optional):
            Iterate the list in reverse order (follow the prev links)
        print_broken_links (optional):
            Print warnings about broken links
        exact_cycles (optional):
            Detect and raise an exception if a cycle is detected in the list

    Yields:
        gdb.Value: The next node in the list.  The value is of the
        specified type.
    Raises:
        :obj:`.CorruptListError`: the list is corrupted
        :obj:`.ListCycleError`: the list contains cycles
        :obj:`BufferError`: portions of the list cannot be read
        :obj:`gdb.NotAvailableError`: The target value is not available.
    """

    for node in list_for_each(list_head, include_head=include_head,
                              reverse=reverse,
                              print_broken_links=print_broken_links,
                              exact_cycles=exact_cycles):
        yield container_of(node, gdbtype, member)

def list_empty(list_head: gdb.Value) -> bool:
    """
    Test whether a list is empty

    Args:
        list_head: The list to test.  The value must be of type
            ``struct list_head`` or ``struct list_head *``.

    Returns:
        :obj:`bool`: Whether the list is empty.

    Raises:
        :obj:`gdb.NotAvailableError`: The target value is not available.
    """
    addr = int(list_head.address)
    if list_head.type.code == gdb.TYPE_CODE_PTR:
        addr = int(list_head)

    return addr == int(list_head['next'])
