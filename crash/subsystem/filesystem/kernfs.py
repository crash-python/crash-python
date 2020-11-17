# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable

from crash.util import get_typed_pointer, AddressSpecifier
from crash.util.symbols import Types
from crash.exceptions import InvalidArgumentError
from crash.types.rbtree import rbtree_postorder_for_each_entry

import gdb

types = Types('struct kernfs_node')

KERNFS_DIR = 1
KERNFS_FILE = 2
KERNFS_LINK = 4

def find_kn(addr: AddressSpecifier) -> gdb.Value:
    """
    Finds ``struct kernfs_node`` by given address.
    Note: Function does no checking whether address points to ``struct
    kernfs_node``. This may change in future.

    Args:
        addr: representation of memory address

    Returns:
        :obj:`gdb.Value`: ``struct kernfs_node``
    """
    kn = get_typed_pointer(addr, types.kernfs_node_type).dereference()
    return kn

def for_each_child(kn: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterates over all child nodes of given kernfs_node.

    Args:
        kn: ``struct kernfs_node`` of directory type

    Yields:
        gdb.Value: ``struct kernfs_node``

    Raises:
        :obj:`.InvalidArgumentError`: kernfs_node is not a directory
    """
    if int(kn['flags']) & KERNFS_DIR == 0:
        raise InvalidArgumentError(f"kernfs_node at {kn.address} is not a directory")

    return rbtree_postorder_for_each_entry(kn['dir']['children'], types.kernfs_node_type, 'rb')

def path_from_node(kn: gdb.Value) -> str:
    """
    Traverses kernfs to root to return node's patch.

    Args:
        kn: ``struct kernfs_node``

    Returns:
        str: path from root to kn (inclusive)
    """
    path = []
    while int(kn['parent']):
        path.append(kn['name'].string())
        kn = kn['parent'].dereference()

    return '/' + '/'.join(path[::-1])
