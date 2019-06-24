# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Type, Any

import gdb

class IncompatibleGDBError(RuntimeError):
    """This version of GDB is incompatible"""
    _fmt = "The installed gdb doesn't provide {}"
    def __init__(self, message: str) -> None:
        super().__init__(self._fmt.format(message))

class MissingSymbolError(RuntimeError):
    """The requested symbol cannot be located."""

class MissingTypeError(RuntimeError):
    """The requested type cannot be located."""

class CorruptedError(RuntimeError):
    """A corrupted data structure has been encountered."""

class DelayedAttributeError(AttributeError):
    """
    The attribute has been declared but the symbol to fill it has not yet been
    located.
    """
    def __init__(self, name: str) -> None:
        msg = "Delayed attribute {} has not been completed."
        self.name = name
        super().__init__(msg.format(name))

class InvalidArgumentError(TypeError):
    """Base class for invalid argument exceptions"""

class ArgumentTypeError(InvalidArgumentError):
    """The provided object could not be converted to the expected type"""
    _fmt = "cannot convert argument `{}' of type {} to {}"

    def __init__(self, name: str, val: Any, expected_type: Type) -> None:
        msg = self._fmt.format(name, self.format_clsname(val.__class__),
                               self.format_clsname(expected_type))
        super().__init__(msg)
        self.val = val

    def format_clsname(self, cls: Type) -> str:
        module = cls.__module__
        if module is None or module == str.__class__.__module__:
            return cls.__name__  # Avoid reporting __builtin__
        return module + '.' + cls.__name__

class UnexpectedGDBTypeBaseError(InvalidArgumentError):
    """Base class for unexpected gdb type exceptions"""

class UnexpectedGDBTypeError(UnexpectedGDBTypeBaseError):
    """The gdb.Type passed describes an inappropriate type for the operation"""
    _fmt = "expected gdb.Type `{}' to describe `{}' not `{}'"
    def __init__(self, name: str, val: gdb.Value,
                 expected_type: gdb.Type) -> None:
        msg = self._fmt.format(name, str(val.type), str(expected_type))
        super().__init__(msg)

class NotStructOrUnionError(UnexpectedGDBTypeBaseError):
    """The provided type is not a struct or union"""
    _fmt = "argument `{}' describes type `{}' which is not a struct or union"
    def __init__(self, name: str, gdbtype: gdb.Type) -> None:
        msg = self._fmt.format(name, str(gdbtype))
        super().__init__(msg)
