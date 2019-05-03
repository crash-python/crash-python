# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from typing import Tuple, Any, Union

import crash.infra
from crash.infra.callback import ObjfileEventCallback
from crash.infra.callback import Callback
from crash.exceptions import DelayedAttributeError

class NamedCallback(ObjfileEventCallback):
    """
    A base class for Callbacks with names

    This cannot be used directly since it does not provide a
    method for :meth:`.ObjfileEventCallback.callback`.

    Args:
        name: The name of the symbol or type to be resolved.
        callback: A function to call with the result of the derived class's
            :meth:`.ObjfileEventCallback.check_ready` method.
        attrname (optional): A name safe for use as an attribute name.
            If unspecified, defaults to the same string as name.

    Attributes:
        name (:obj:`str`): The name of the symbol or type being resolved.
        attrname (:obj:`str`): The name of symbol or type being resolved
            translated for use as an attribute name.
    """
    def __init__(self, name: str, callback: Callback, attrname: str=None):
        super().__init__()

        self.name = name
        self.attrname = self.name

        if attrname is not None:
            self.attrname = attrname

        self._callback = callback

    def callback(self, result: Any) -> Union[None, bool]:
        """
        The callback for handling the sucessful result of :meth:`check_ready`.

        It indirectly calls the callback specified in the constructor.

        Args:
            result: The result returned from :meth:`check_ready`

        Returns:
            :obj:`None` or :obj:`bool`: If :obj:`None` or :obj:`True`,
            the callback succeeded and will be completed and removed.
            Otherwise, the callback will stay connected for future completion.
        """
        return self._callback(result)

class MinimalSymbolCallback(NamedCallback):
    """
    A callback that executes when the named minimal symbol is
    discovered in the objfile and returns the :obj:`gdb.MinSymbol`.

    The callback must accept a :obj:`gdb.MinSymbol` and return
    :obj:`bool` or :obj:`None`.

    Args:
        name: The name of the minimal symbol to discover
        callback: The callback to execute when the minimal symbol is discovered
        symbol_file (optional): Name of the symbol file to use
    """
    def __init__(self, name: str, callback: Callback, symbol_file: str=None):
        super().__init__(name, callback)

        self.symbol_file = symbol_file

        self.connect_callback()

    def check_ready(self) -> gdb.MinSymbol:
        """
        Returns the result of looking up the minimal symbol when a new
        object file is loaded.

        Returns:
            :obj:`gdb.MinSymbol`: The requested minimal symbol
        """
        return gdb.lookup_minimal_symbol(self.name, self.symbol_file, None)

    def __str__(self):
        return ("<{}({}, {}, {})>"
                .format(self.__class__.__name__, self.name,
                        self.symbol_file, self.callback))

class SymbolCallback(NamedCallback):
    """
    A callback that executes when the named symbol is discovered in the
    objfile and returns the :obj:`gdb.Symbol`.

    The callback must accept a :obj:`gdb.Symbol` and return :obj:`bool`
    or :obj:`None`.

    Args:
        name: The name of the symbol to discover
        callback: The callback to execute when the symbol is discovered
        domain (optional): The domain to search for the symbol.  The value
          is assumed to be one of the value associated with :obj:`gdb.Symbol`
          constant, i.e. SYMBOL_*_DOMAIN.
    """
    def __init__(self, name: str, callback: Callback,
                 domain: int=gdb.SYMBOL_VAR_DOMAIN):
        super().__init__(name, callback)

        self.domain = domain

        self.connect_callback()

    def check_ready(self) -> gdb.Symbol:
        """
        Returns the result of looking up the symbol when a new object
        file is loaded.

        Returns:
            :obj:`gdb.Symbol`: The requested symbol
        """
        return gdb.lookup_symbol(self.name, None, self.domain)[0]

    def __str__(self):
        return ("<{}({}, {})>"
                .format(self.__class__.__name__, self.name, self.domain))

class SymvalCallback(SymbolCallback):
    """
    A callback that executes when the named symbol is discovered in the
    objfile and returns the :obj:`gdb.Value` associated with the
    :obj:`gdb.Symbol`.

    The callback must accept a :obj:`gdb.Value` and return :obj:`bool`
    or :obj:`None`.

    See :obj:`SymbolCallback` for arguments.
    """
    def check_ready(self) -> gdb.Value:
        """
        After successfully looking up the :obj:`gdb.Symbol`, returns
        the :obj:`gdb.Value` associated with it.

        Returns:
            :obj:`gdb.Value`: The value associated with the requested symbol
        """
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
    objfile and returns the :obj:`gdb.Type` associated with it.

    The callback must accept a :obj:`gdb.Type` and return :obj:`bool`
    or :obj:`None`.

    Args:
        name: The name of the type to discover
        callback: The callback to execute when the type is discovered
        block (optional): The :obj:`gdb.Block` to search for the symbol

    """
    def __init__(self, name: str, callback: Callback, block: gdb.Block=None):
        (name, attrname, self.pointer) = self.resolve_type(name)

        super().__init__(name, callback, attrname)

        self.block = block

        self.connect_callback()

    @staticmethod
    def resolve_type(name: str) -> Tuple[str, str, bool]:
        """
        This function takes a C type name and translates it into a 3-tuple
        that contains the basic type name, the type name translated to
        a form suitable for an attribute name, and whether the type
        corresponds to a pointer.

        The basic type name has all leading and trailing whitespace stripped,
        and any ``*`` removed.

        The attribute type name takes that base, removes the leading
        ``struct`` for structure types, removes any leading or trailing
        whitespace, replaces internal spaces with underscores, and appends
        a ``_type`` or ``_p_type`` suffix, depending on whether the type
        is a pointer type.

        Some examples:

        - ``struct foo`` → ``foo_type``
        - ``struct foo *`` → ``foo_p_type``
        - ``unsigned long`` → ``unsigned_long_type``

        *Notes*:
            - Multiple levels of pointers are not handled properly.  In
                practice this means that ``struct foo *`` and
                ``struct foo **`` can't be used simultaneously.  This is
                typically not a problem.
            - Unions are not handled as a special case as structs are.  A
                union type would use an attribute name of ``union_foo_type``.

        Returns:
            (:obj:`str`, :obj:`str`, :obj:`bool`): A 3-tuple consisting of
            the basic type name, the name formatted for use as an attribute
            name, and whether the type is a pointer type.
        """
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

    Args:
        name: The name of the minimal symbol
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.cb = MinimalSymbolCallback(name, self.callback)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class DelayedSymbol(DelayedValue):
    """
    A DelayedValue that handles symbols.

    Args:
        name: The name of the symbol
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.cb = SymbolCallback(name, self.callback)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class DelayedType(DelayedValue):
    """
    A DelayedValue for types.

    Args:
        name: The name of the type.
    """
    def __init__(self, name: str):
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
    A :obj:`DelayedSymbol` that returns the :obj:`gdb.Value`
    associated with the symbol.

    Args:
        name: The name of the symbol.
    """
    def callback(self, value: gdb.Symbol) -> None:
        symval = value.value()
        if symval.type.code == gdb.TYPE_CODE_FUNC:
            symval = symval.address
        self.value = symval

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class DelayedMinimalSymval(DelayedMinimalSymbol):
    """
    A DelayedMinimalSymbol that returns the address of the
    minimal symbol as an :obj:`int`.

    Args:
        name: The name of the minimal symbol.
    """
    def callback(self, value: gdb.MinSymbol) -> None:
        self.value = int(value.value().address)

    def __str__(self):
        return "{} attached with {}".format(self.__class__, str(self.cb))

class ClassProperty(object):
    def __init__(self, get):
        self.get = get

    def __get__(self, instance, owner):
        return self.get()

class DelayedLookups(object):
    """
    A class for handling dynamic creation of class attributes that
    contain delayed values.  The attributes are specified using
    special names.  These are documented in the _CrashBaseMeta
    documentation.
    """
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
                t = DelayedType(typ)
                cls.add_lookup(clsname, dct, t.name, t, t.attrname)
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
                cb = getattr(cls, callback)
                callbacks.append(TypeCallback(typ, cb))
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


