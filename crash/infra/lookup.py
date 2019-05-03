# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

import crash.infra
from crash.infra.callback import ObjfileEventCallback
from crash.exceptions import DelayedAttributeError

class NamedCallback(ObjfileEventCallback):
    """
    A base class for Callbacks with names
    """
    def __init__(self, name, attrname=None):
        super().__init__()

        self.name = name
        self.attrname = self.name

        if attrname is not None:
            self.attrname = attrname

class MinimalSymbolCallback(NamedCallback):
    """
    A callback that executes when the named minimal symbol is
    discovered in the objfile and returns the gdb.MinimalSymbol.
    """
    def __init__(self, name, callback, symbol_file=None):
        """
        Args:
            name (str): The name of the minimal symbol to discover
            callback (method): The callback to execute when the minimal
                symbol is discovered
            symbol_file (str, optional, default=None): Name of symbol file
        """
        super().__init__(name)

        self.symbol_file = symbol_file
        self.callback = callback

        self.connect_callback()

    def check_ready(self):
        return gdb.lookup_minimal_symbol(self.name, self.symbol_file, None)
    def __str__(self):
        return ("<{}({}, {}, {})>"
                .format(self.__class__.__name__, self.name,
                        self.symbol_file, self.callback))

class SymbolCallback(NamedCallback):
    """
    A callback that executes when the named symbol is discovered in the
    objfile and returns the gdb.Symbol.
    """
    def __init__(self, name, callback, domain=gdb.SYMBOL_VAR_DOMAIN):
        """
        Args:
            name (str): The name of the symbol to discover
            callbacks (method): The callback to execute when the minimal
                symbol is discover
            domain (gdb.Symbol constant, i.e. SYMBOL_*_DOMAIN): The domain
                to search for the symbol
        """
        super().__init__(name)

        self.domain = domain
        self.callback = callback

        self.connect_callback()

    def check_ready(self):
        return gdb.lookup_symbol(self.name, None, self.domain)[0]

    def __str__(self):
        return ("<{}({}, {})>"
                .format(self.__class__.__name__, self.name, self.domain))

class SymvalCallback(SymbolCallback):
    """
    A callback that executes when the named symbol is discovered in the
    objfile and returns the gdb.Value associated with it.
    """
    def check_ready(self):
        sym = super().check_ready()
        if sym is not None:
            try:
                return sym.value()
            except gdb.MemoryError:
                pass
        return None

class TypeCallback(NamedCallback):
    """
    A callback that executes when the named type is discovered in the
    objfile and returns the gdb.Type associated with it.
    """
    def __init__(self, name, callback, block=None):
        (name, attrname, self.pointer) = self.resolve_type(name)

        super().__init__(name, attrname)

        self.block = block
        self.callback = callback

        self.connect_callback()

    @staticmethod
    def resolve_type(name):
        pointer = False
        name = name.strip()
        if name[-1] == '*':
            pointer = True
            name = name[:-1].strip()

        attrname = name
        if name.startswith('struct '):
            attrname = name[7:].strip()

        if pointer:
            attrname += '_p_type'
        else:
            attrname += '_type'

        name = name
        attrname = attrname.replace(' ', '_')

        return (name, attrname, pointer)

    def check_ready(self):
        try:
            return gdb.lookup_type(self.name, self.block)
        except gdb.error as e:
            return None

    def __str__(self):
        return ("<{}({}, {})>"
                .format(self.__class__.__name__, self.name, self.block))

class DelayedValue(object):
    """
    A generic class for making class attributes available that describe
    to-be-loaded symbols, minimal symbols, and types.
    """
    def __init__(self, name, attrname=None):
        self.name = name
        self.attrname = attrname
        if self.attrname is None:
            self.attrname = name
        self.value = None

    def get(self):
        if self.value is None:
            raise DelayedAttributeError(self.name)
        return self.value

    def callback(self, value):
        if self.value is not None:
            return
        self.value = value

class DelayedMinimalSymbol(DelayedValue):
    """
    A DelayedValue that handles minimal symbols.
    """
    def __init__(self, name):
        """
        Args:
            name (str): The name of the minimal symbol
        """
        super().__init__(name)
        self.cb = MinimalSymbolCallback(name, self.callback)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class DelayedSymbol(DelayedValue):
    """
    A DelayedValue that handles symbols.
    """
    def __init__(self, name):
        """
        Args:
            name (str): The name of the symbol
        """
        super().__init__(name)
        self.cb = SymbolCallback(name, self.callback)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class DelayedType(DelayedValue):
    """
    A DelayedValue for types.
    """
    def __init__(self, name):
        """
        Args:
            name (str): The name of the type.
        """
        (name, attrname, self.pointer) = TypeCallback.resolve_type(name)
        super().__init__(name, attrname)
        self.cb = TypeCallback(name, self.callback)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.callback))

    def callback(self, value):
        if self.pointer:
            value = value.pointer()
        self.value = value

class DelayedSymval(DelayedSymbol):
    """
    A DelayedSymbol that returns the gdb.Value associated with the symbol.
    """
    def callback(self, value):
        symval = value.value()
        if symval.type.code == gdb.TYPE_CODE_FUNC:
            symval = symval.address
        self.value = symval

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class DelayedMinimalSymval(DelayedMinimalSymbol):
    """
    A DelayedMinimalSymbol that returns the address of the
    minimal symbol as a int.
    """
    def callback(self, value):
        self.value = int(value.value().address)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))
