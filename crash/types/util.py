#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

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

charp = gdb.lookup_type('char').pointer()
def container_of(val, gdbtype, member):
    gdbtype = resolve_type(gdbtype)
    offset = offsetof(gdbtype, member)
    return (val.cast(charp) - offset).cast(gdbtype.pointer()).dereference()
