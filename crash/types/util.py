#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

class OffsetOfError(Exception):
    """Generic Exception for offsetof errors"""
    def __init__(self, message):
        super(OffsetOfError, self).__init__()
        self.message = message

    def __str__(self):
        return self.message

class InvalidArgumentError(OffsetOfError):
    """The provided object could not be converted to gdb.Type"""
    formatter = "cannot convert {} to gdb.Type"

    def __init__(self, val):
        msg = self.formatter.format(str(type(val)))
        super(InvalidArgumentError, self).__init__(msg)
        self.val = val

class InvalidArgumentTypeError(OffsetOfError):
    """The provided type is not a struct or union"""
    formatter = "`{}' is not a struct or union"
    def __init__(self, gdbtype):
        msg = self.formatter.format(str(gdbtype))
        super(InvalidArgumentTypeError, self).__init__(msg)
        self.type = gdbtype

class InvalidComponentError(OffsetOfError):
    """An error occured while resolving the member specification"""
    formatter = "cannot resolve '{}->{}' ({})"
    def __init__(self, gdbtype, spec, message):
        msg = self.formatter.format(str(gdbtype), spec, message)
        super(InvalidComponentError, self).__init__(msg)
        self.type = gdbtype
        self.spec = spec

# These exceptions are only raised by _offsetof and should not be
# visible outside of this module.
class _InvalidComponentBaseError(OffsetOfError):
    """An internal error occured while resolving the member specification"""
    pass

class _InvalidComponentTypeError(_InvalidComponentBaseError):
    """The component expects the type to be a struct or union but it is not."""
    formatter = "component `{}' in `{}' is not a struct or union"
    def __init__(self, name, spec):
        msg = self.formatter.format(name, spec)
        super(_InvalidComponentTypeError, self).__init__(msg)
        self.name = name
        self.spec = spec

class _InvalidComponentNameError(_InvalidComponentBaseError):
    """The requested member component does not exist in the provided type."""

    formatter = "no such member `{}' in `{}'"
    def __init__(self, member, gdbtype):
        msg = self.formatter.format(member, str(gdbtype))
        super(_InvalidComponentNameError, self).__init__(msg)
        self.member = member
        self.type = gdbtype

def get_symbol_value(symname):
    return gdb.lookup_symbol(symname, None)[0].value()

def safe_get_symbol_value(symname):
    sym = gdb.lookup_symbol(symname, None)[0]

    if sym is not None:
        return sym.value()
    else:
        return None

def resolve_type(val):
    if isinstance(val, gdb.Type):
        gdbtype = val
    elif isinstance(val, gdb.Value):
        gdbtype = val.type
    elif isinstance(val, str):
        gdbtype = gdb.lookup_type(val)
    elif isinstance(val, gdb.Symbol):
        gdbtype = val.value().type
    else:
        raise TypeError("Invalid type {}".format(str(type(val))))
    return gdbtype

def __offsetof(val, spec, error):
    gdbtype = val
    offset = 0

    for member in spec.split('.'):
        found = False
        if gdbtype.code != gdb.TYPE_CODE_STRUCT and \
           gdbtype.code != gdb.TYPE_CODE_UNION:
            raise _InvalidComponentTypeError(field.name, spec)
        for field in gdbtype.fields():
            off = field.bitpos >> 3
            if field.name == member:
                found = True
                break

            # Step into anonymous structs and unions
            if field.name is None:
                res = __offsetof(field.type, member, False)
                if res is not None:
                    found = True
                    off += res
                    break
        if not found:
            if error:
                raise _InvalidComponentNameError(member, gdbtype)
            else:
                return None
        gdbtype = field.type
        offset += off

    return offset

def offsetof(val, spec, error=True):
    gdbtype = None
    try:
        gdbtype = resolve_type(val)
    except gdb.error as e:
        pass
    except TypeError as e:
        pass

    if not isinstance(gdbtype, gdb.Type):
        raise InvalidArgumentError(val)

    # We'll be friendly and accept pointers as the initial type
    if gdbtype.code == gdb.TYPE_CODE_PTR:
        gdbtype = gdbtype.target()

    if gdbtype.code != gdb.TYPE_CODE_STRUCT and \
       gdbtype.code != gdb.TYPE_CODE_UNION:
        raise InvalidArgumentTypeError(gdbtype)

    try:
        return __offsetof(gdbtype, spec, error)
    except _InvalidComponentBaseError as e:
        if error:
            raise InvalidComponentError(gdbtype, spec, e.message)
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

