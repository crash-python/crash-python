#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

charp = gdb.lookup_type('char').pointer()

def resolve_type(val):
    if isinstance(val, str):
        gdbtype = gdb.lookup_gdbtype(val)
    elif isinstance(val, gdb.Value):
        gdbtype = val.gdbtype
    else:
        gdbtype = val
    return gdbtype

def offsetof(val, member):
    gdbtype = resolve_type(val)
    if not isinstance(val, gdb.Type):
        raise TypeError("offsetof requires gdb.Type or a string/value that can be used to lookup a gdb.Type")

    return gdbtype[member].bitpos >> 3

def container_of(val, gdbtype, member):
    gdbtype = resolve_type(gdbtype)
    offset = offsetof(gdbtype, member)
    return (val.cast(charp) - offset).cast(gdbtype.pointer()).dereference()

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

def per_cpu(symbol, cpu):
    if isinstance(symbol, str):
        symbol = gdb.lookup_global_symbol(symbol).value()
    elif isinstance(symbol, gdb.Symbol):
        symbol = symbol.value()
    else:
        raise TypeError("Must be string or gdb.Symbol")

    percpu_addr = symbol.address.cast(charp) + per_cpu_offset[cpu]
    return percpu_addr.cast(symbol.type.pointer()).dereference()
