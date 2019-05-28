# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

class MissingSymbolError(RuntimeError):
    """The requested symbol cannot be located."""
    pass

class MissingTypeError(RuntimeError):
    """The requested type cannot be located."""
    pass

class CorruptedError(RuntimeError):
    """A corrupted data structure has been encountered."""
    pass

class DelayedAttributeError(AttributeError):
    """
    The attribute has been declared but the symbol to fill it has not yet been
    located.
    """
    def __init__(self, name):
        msg = "Delayed attribute {} has not been completed."
        self.name = name
        super().__init__(msg.format(name))

class InvalidArgumentError(TypeError):
    """Base class for invalid argument exceptions"""
    def __init__(self, msg):
        super().__init__(msg)

class ArgumentTypeError(InvalidArgumentError):
    """The provided object could not be converted to the expected type"""
    formatter = "cannot convert argument `{}' of type {} to {}"

    def __init__(self, name, val, expected_type):
        msg = self.formatter.format(name, self.format_clsname(val.__class__),
                                    self.format_clsname(expected_type))
        super().__init__(msg)
        self.val = val

    def format_clsname(self, cls):
        module = cls.__module__
        if module is None or module == str.__class__.__module__:
            return cls.__name__  # Avoid reporting __builtin__
        else:
            return module + '.' + cls.__name__

class UnexpectedGDBTypeError(InvalidArgumentError):
    """The gdb.Type passed describes an inappropriate type for the operation"""
    formatter = "expected gdb.Type `{}' to describe `{}' not `{}'"
    def __init__(self, name, gdbtype, expected_type):
        msg = self.formatter.format(name, str(gdbtype), str(expected_type))
        super().__init__(msg)

class NotStructOrUnionError(UnexpectedGDBTypeError):
    """The provided type is not a struct or union"""
    formatter = "argument `{}' describes type `{}' which is not a struct or union"
    def __init__(self, name, gdbtype):
        super().__init__(name, gdbtype, gdbtype)
        msg = self.formatter.format(name, str(gdbtype))
