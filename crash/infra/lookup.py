# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gdb
import sys

if sys.version_info.major >= 3:
    long = int

import crash.infra
from crash.infra.callback import ObjfileEventCallback
from crash.exceptions import DelayedAttributeError

class MinimalSymbolCallback(ObjfileEventCallback):
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
        self.name = name
        self.symbol_file = symbol_file
        self.callback = callback
        super(MinimalSymbolCallback, self).__init__()

    def check_ready(self):
        return gdb.lookup_minimal_symbol(self.name, self.symbol_file, None)
    def __str__(self):
        return ("<{}({}, {}, {})>"
                .format(self.__class__.__name__, self.name,
                        self.symbol_file, self.callback))

class SymbolCallback(ObjfileEventCallback):
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
        self.name = name
        self.domain = domain
        self.callback = callback
        super(SymbolCallback, self).__init__()

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
        sym = super(SymvalCallback, self).check_ready()
        if sym is not None:
            try:
                return sym.value()
            except gdb.MemoryError:
                pass
        return None

class TypeCallback(ObjfileEventCallback):
    """
    A callback that executes when the named type is discovered in the
    objfile and returns the gdb.Type associated with it.
    """
    def __init__(self, name, callback, block=None):
        self.name = name
        self.block = block
        self.callback = callback
        super(TypeCallback, self).__init__()

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
    def __init__(self, name):
        self.name = name
        self.value = None

    def get(self, owner):
        if self.value is None:
            raise DelayedAttributeError(owner, self.name)
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
        super(DelayedMinimalSymbol, self).__init__(name)
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
        super(DelayedSymbol, self).__init__(name)
        self.cb = SymbolCallback(name, self.callback)
    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class DelayedType(DelayedValue):
    """
    A DelayedValue for types.
    """
    def __init__(self, name, pointer=False):
        """
        Args:
            name (str): The name of the type.  Must not be a pointer type.
            pointer (bool, optional, default=False): Whether the requested
                type should be returned as a pointer to that type.
        """
        super(DelayedType, self).__init__(name)
        self.pointer = pointer
        self.cb = TypeCallback(name, self.callback)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

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
    minimal symbol as a long.
    """
    def callback(self, value):
        self.value = long(value.value().address)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class ClassProperty(object):
    def __init__(self, get):
        self.get = get

    def __get__(self, instance, owner):
        return self.get(owner)

class DelayedLookups(object):
    """
    A class for handling dynamic creation of class attributes that
    contain delayed values.  The attributes are specified using
    special names.  These are documented in the _CrashBaseMeta
    documentation.
    """
    @classmethod
    def _resolve_type(cls, name):
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

        attrname = attrname.replace(' ', '_')
        return (name, attrname, pointer)

    @classmethod
    def name_check(cls, dct, name, attrname):
        try:
            collision = dct['__delayed_lookups__'][attrname]
        except KeyError:
            return

        raise NameError("DelayedLookup name collision: `{}' and `{}' -> `{}'"
                        .format(name, collision.name, attrname))

    @classmethod
    def add_lookup(cls, clsname, dct, name, attr, attrname=None):
        if attrname is None:
            attrname = name
        cls.name_check(dct, name, attrname)
        dct['__delayed_lookups__'][attrname] = attr
        if attrname.startswith('__'):
            attrname = '_{}{}'.format(clsname, attrname)
        dct[attrname] = ClassProperty(attr.get)

    @classmethod
    def setup_delayed_lookups_for_class(cls, clsname, dct):
        if '__delayed_lookups__' in dct:
            raise NameError("Name `delayed_lookups' is reserved when using DelayedLookups")
        dct['__delayed_lookups__'] = {}

        if '__types__' in dct:
            if not isinstance(dct['__types__'], list):
                raise TypeError('__types__ attribute must be a list of strings')
            for typ in dct['__types__']:
                (lookupname, attrname, pointer) = cls._resolve_type(typ)
                cls.add_lookup(clsname, dct, lookupname,
                               DelayedType(lookupname, pointer), attrname)
            del dct['__types__']
        if '__symbols__' in dct:
            if not isinstance(dct['__symbols__'], list):
                raise TypeError('__symbols__ attribute must be a list of strings')
            for symname in dct['__symbols__']:
                cls.add_lookup(clsname, dct, symname, DelayedSymbol(symname))
            del dct['__symbols__']
        if '__minsymbols__' in dct:
            if not isinstance(dct['__minsymbols__'], list):
                raise TypeError('__minsymbols_ attribute must be a list of strings')
            for symname in dct['__minsymbols__']:
                cls.add_lookup(clsname, dct, symname,
                               DelayedMinimalSymbol(symname))
            del dct['__minsymbols__']
        if '__symvals__' in dct:
            if not isinstance(dct['__symvals__'], list):
                raise TypeError('__symvals__ attribute must be a list of strings')
            for symname in dct['__symvals__']:
                cls.add_lookup(clsname, dct, symname, DelayedSymval(symname))
            del dct['__symvals__']

        if '__minsymvals__' in dct:
            if not isinstance(dct['__minsymvals__'], list):
                raise TypeError('__minsymvals__ attribute must be a list of strings')
            for symname in dct['__minsymvals__']:
                cls.add_lookup(clsname, dct, symname,
                               DelayedMinimalSymval(symname))
            del dct['__minsymvals__']

        if '__delayed_values__' in dct:
            if not isinstance(dct['__delayed_values__'], list):
                raise TypeError('__delayed_values__ attribute must be a list of strings')
            for propname in dct['__delayed_values__']:
                cls.add_lookup(clsname, dct, propname, DelayedValue(propname))
            del dct['__delayed_values__']

    @classmethod
    def setup_named_callbacks(this_cls, cls, dct):
        callbacks = []
        if '__type_callbacks__' in dct:
            for (typ, callback) in dct['__type_callbacks__']:
                (lookupname, attrname, pointer) = this_cls._resolve_type(typ)
                cb = getattr(cls, callback)
                callbacks.append(TypeCallback(lookupname, cb))
            del dct['__type_callbacks__']

        if '__symbol_callbacks__' in dct:
            for (sym, callback) in dct['__symbol_callbacks__']:
                cb = getattr(cls, callback)
                callbacks.append(SymbolCallback(sym, cb))
            del dct['__symbol_callbacks__']
        if '__minsymbol_callbacks__' in dct:
            for (sym, callback) in dct['__minsymbol_callbacks__']:
                cb = getattr(cls, callback)
                callbacks.append(MinimalSymbolCallback(sym, cb))
            del dct['__minsymbol_callbacks__']
        if callbacks:
            dct['__delayed_lookups__']['__callbacks__'] = callbacks

def get_delayed_lookup(cls, name):
    return cls.__delayed_lookups__[name]


