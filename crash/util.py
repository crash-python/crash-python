# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from crash.infra import CrashBaseClass, export
from crash.exceptions import MissingTypeError, MissingSymbolError

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

class TypesUtilClass(CrashBaseClass):
    __types__ = [ 'char *' ]

    @export
    def container_of(self, val, gdbtype, member):
        if not isinstance(val, gdb.Value):
            raise TypeError("container_of expects gdb.Value")
        charp = self.char_p_type
        if val.type.code != gdb.TYPE_CODE_PTR:
            val = val.address
        gdbtype = resolve_type(gdbtype)
        offset = offsetof(gdbtype, member)
        return (val.cast(charp) - offset).cast(gdbtype.pointer()).dereference()

    @export
    @staticmethod
    def get_symbol_value(symname, block=None, domain=None):
        if domain is None:
            domain = gdb.SYMBOL_VAR_DOMAIN
        sym = gdb.lookup_symbol(symname, block, domain)[0]
        if sym:
            return sym.value()
        raise MissingSymbolError("Cannot locate symbol {}".format(symname))

    @export
    @classmethod
    def safe_get_symbol_value(cls, symname, block=None, domain=None):
        try:
            return cls.get_symbol_value(symname, block, domain)
        except MissingSymbolError:
            return None

    @export
    @staticmethod
    def resolve_type(val):
        if isinstance(val, gdb.Type):
            gdbtype = val
        elif isinstance(val, gdb.Value):
            gdbtype = val.type
        elif isinstance(val, str):
            try:
                gdbtype = gdb.lookup_type(val)
            except gdb.error:
                raise MissingTypeError("Could not resolve type {}"
                                       .format(val))
        elif isinstance(val, gdb.Symbol):
            gdbtype = val.value().type
        else:
            raise TypeError("Invalid type {}".format(str(type(val))))
        return gdbtype

    @classmethod
    def __offsetof(cls, val, spec, error):
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
                    nexttype = field.type
                    found = True
                    break

                # Step into anonymous structs and unions
                if field.name is None:
                    res = cls.__offsetof(field.type, member, False)
                    if res is not None:
                        found = True
                        off += res[0]
                        nexttype = res[1]
                        break
            if not found:
                if error:
                    raise _InvalidComponentNameError(member, gdbtype)
                else:
                    return None
            gdbtype = nexttype
            offset += off

        return (offset, gdbtype)

    @export
    @classmethod
    def offsetof_type(cls, val, spec, error=True):
        gdbtype = None
        try:
            gdbtype = resolve_type(val)
        except MissingTypeError as e:
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
            return cls.__offsetof(gdbtype, spec, error)
        except _InvalidComponentBaseError as e:
            if error:
                raise InvalidComponentError(gdbtype, spec, e.message)
            else:
                return None

    @export
    @classmethod
    def offsetof(cls, val, spec, error=True):
        res = cls.offsetof_type(val, spec, error)
        if res:
            return res[0]
        return None

    @export
    @classmethod
    def find_member_variant(cls, gdbtype, variants):
        for v in variants:
            if cls.offsetof(gdbtype, v, False) is not None:
                return v
        raise TypeError("Unrecognized '{}': could not find member '{}'"
                        .format(str(gdbtype), variants[0]))

    @export
    @staticmethod
    def safe_lookup_type(name, block=None):
        try:
            return gdb.lookup_type(name, block)
        except gdb.error:
            return None

    @export
    @staticmethod
    def array_size(value):
        return value.type.sizeof // value[0].type.sizeof

    @export
    @staticmethod
    def get_typed_pointer(val, gdbtype):
        if gdbtype.code != gdb.TYPE_CODE_PTR:
            gdbtype = gdbtype.pointer()
        if isinstance(val, gdb.Value):
            if (val.type != gdbtype and
                val.type != gdbtype.target()):
                raise TypeError("gdb.Value must refer to {} not {}"
                                .format(gdbtype, val.type))
        elif isinstance(val, str):
            try:
                val = long(val, 16)
            except TypeError as e:
                print(e)
                raise TypeError("string must describe hex address: ".format(e))
        if isinstance(val, long):
            val = gdb.Value(val).cast(gdbtype).dereference()

        return val

