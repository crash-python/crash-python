# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

def skip_with_type(typename):
    try:
        gdbtype = gdb.lookup_type(typename)
        return unittest.skip(f"found type {typename}")
    except gdb.error:
        pass

    return lambda func: func

def skip_without_type(typename):
    try:
        gdbtype = gdb.lookup_type(typename)
    except gdb.error:
        return unittest.skip(f"missing type {typename}")

    return lambda func: func

def skip_with_symbol(symname):
    symbol = gdb.lookup_symbol(symname, None)[0]
    if symbol is not None:
        return unittest.skip(f"found symbol {symname}")

    return lambda func: func

def skip_without_symbol(symname):
    symbol = gdb.lookup_symbol(symname, None)[0]
    if symbol is None:
        return unittest.skip(f"missing symbol {symname}")

    return lambda func: func

def has_super_blocks(name):
    from crash.subsystem.filesystem import for_each_super_block
    for sb in for_each_super_block():
        if sb['s_type']['name'].string() == name:
            return True
    return False

can_test = {}

def skip_with_supers(name):
    if not name in can_test:
        can_test[name] = has_super_blocks(name)

    if not can_test[name]:
        return lambda func: func

    return unittest.skip(f"{name} file systems in image")

def skip_without_supers(name):
    if not name in can_test:
        can_test[name] = has_super_blocks(name)

    if can_test[name]:
        return lambda func: func

    return unittest.skip(f"no {name} file systems in image")
