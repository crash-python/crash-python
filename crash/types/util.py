#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

def get_symbol_value(symname):
    return gdb.lookup_symbol(symname, None)[0].value()

def safe_get_symbol_value(symname):
    sym = gdb.lookup_symbol(symname, None)[0]

    if sym is not None:
        return sym.value()
    else:
        return None

def resolve_type(val):
    if isinstance(val, str):
        gdbtype = gdb.lookup_type(val)
    elif isinstance(val, gdb.Value):
        gdbtype = val.type
    else:
        gdbtype = val
    return gdbtype

def offsetof(val, member, error=True):
    gdbtype = resolve_type(val)
    if not isinstance(val, gdb.Type):
        raise TypeError("offsetof requires gdb.Type or a string/value that can be used to lookup a gdb.Type")

    try:
        for field in list(gdbtype.values()):
            off = field.bitpos >> 3
            if field.name == member:
                return off
            res = offsetof(field.type, member, False)
            if res is not None:
                return res + off
    except TypeError as e:
        # not iterable, skip
        pass

    if error:
        raise TypeError("offsetof couldn't find member '%s' in type '%s'" 
                            % (member, str(gdbtype)))
    else:
        return None

charp = gdb.lookup_type('char').pointer()
def container_of(val, gdbtype, member):
    gdbtype = resolve_type(gdbtype)
    offset = offsetof(gdbtype, member)
    return (val.cast(charp) - offset).cast(gdbtype.pointer()).dereference()

def find_member_variant(gdbtype, variants):
    for v in variants:
        if offsetof(gdbtype, v, False) is not None:
            return v
    raise TypeError("Unrecognized '%s': could not find member '%s'" %
                        (str(gdbtype), variants[0]))

def safe_lookup_type(name):
    try:
        return gdb.lookup_type(name)
    except gdb.error:
        return None

