# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Optional, Iterable

import gdb

from crash.util import container_of
from crash.util.symbols import Types
from crash.exceptions import ArgumentTypeError, UnexpectedGDBTypeError

class TreeError(Exception):
    pass

class CorruptTreeError(TreeError):
    pass

types = Types(['struct rb_root', 'struct rb_node'])

def _rb_left_deepest_node(node: gdb.Value) -> Optional[gdb.Value]:
    while int(node) != 0:
        if int(node['rb_left']) != 0:
            node = node['rb_left']
        elif int(node['rb_right']) != 0:
            node = node['rb_right']
        else:
            return node

    return None

def _rb_parent(node: gdb.Value) -> Optional[gdb.Value]:
    addr = int(node['__rb_parent_color'])
    addr &= ~0x3
    if addr == 0:
        return None
    return gdb.Value(addr).cast(node.type)

def _rb_next_postorder(node: gdb.Value) -> Optional[gdb.Value]:
    if int(node) == 0:
        return None

    parent = _rb_parent(node)
    if (parent is not None and int(node) == int(parent['rb_left']) and
            int(parent['rb_right']) != 0):
        return _rb_left_deepest_node(parent['rb_right'])

    return parent

def rbtree_postorder_for_each(root: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterate over nodes of a rooted RB tree in post-order fashion

    Args:
        root: The tree to iterate.  The value must be of type
            ``struct rb_root`` or ``struct rb_root *``.

    Yields:
        gdb.Value: The next node of the tree. The value is
        of type ``struct rb_node``.

    Raises:
        :obj:`.CorruptTreeError`: the list is corrupted
    """
    if not isinstance(root, gdb.Value):
        raise ArgumentTypeError('root', root, gdb.Value)
    if root.type == types.rb_root_type.pointer():
        root = root.dereference()
    elif root.type != types.rb_root_type:
        raise UnexpectedGDBTypeError('root', root, types.rb_root_type)

    if root.type is not types.rb_root_type:
        types.override('struct rb_root', root.type)

    if int(root.address) == 0:
        raise CorruptTreeError("root is NULL pointer")

    node = _rb_left_deepest_node(root['rb_node'])

    while node is not None:
        yield node.dereference()
        node = _rb_next_postorder(node)

def rbtree_postorder_for_each_entry(root: gdb.Value,
                                    gdbtype: gdb.Type, member: str) -> Iterable[gdb.Value]:
    """
    Iterate over nodes of a rooted RB tree in post-order fashion and yield each
    node's containing object

    Args:
        root: The tree to iterate.  The value must be of type
            ``struct rb_root`` or ``struct rb_root *``.
        gdbtype: The type of the containing object
        member: The name of the member in the containing object that
            corresponds to the rb_node

    Yields:
        gdb.Value: The next node of the tree. The value is
        of the specified type.

    Raises:
        :obj:`.CorruptTreeError`: the list is corrupted
    """
    for node in rbtree_postorder_for_each(root):
        yield container_of(node, gdbtype, member)
