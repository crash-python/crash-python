# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
The crash.util.symbols module provides a mechanism to simply discover
and resolve symbols, types, minimal symbols, and values.

A typical use is declaring a DelayedCollection at the top of a module and
using the DelayedCollection within the classes and functions that are
a part of the module.

Each of the collections defined here are instantiated using a list of
names that each collection type will resolve into a type, a symbol, a minimal
symbol, etc.  The names will by available as dictionary keys and also as
attribute names.  In the latter case, the names will be resolved into
a form usable as an attribute name.  See :class:`.Types` for more information.
"""

from typing import Type, List, Tuple, Callable, Union, Dict, Any

import gdb

from crash.infra.lookup import DelayedType, DelayedSymbol, DelayedSymval
from crash.infra.lookup import DelayedValue, DelayedMinimalSymbol
from crash.infra.lookup import DelayedMinimalSymval
from crash.infra.lookup import NamedCallback, TypeCallback
from crash.infra.lookup import SymbolCallback, MinimalSymbolCallback
from crash.exceptions import DelayedAttributeError

CollectedValue = Union[gdb.Type, gdb.Value, gdb.Symbol, gdb.MinSymbol, Any]
Names = Union[List[str], str]

class DelayedCollection:
    """
    A generic container for delayed lookups.

    In addition to the :meth:`get` method, the names are also accessible
    via attribute names (``__getattr__``) or dictionary keys (``__getitem__``).

    Args:
        cls: The type of :obj:`.DelayedValue` to be collected
        names: The names of all the symbols to be collected

    Attributes:
        attrs (:obj:`dict`): A dictionary that maps the attribute names
            to the :obj:`.DelayedValue` object associated with each one.
            While the ``__getattr__`` and ``__getitem__`` methods will
            return the contained object.  This dictionary will contain
            the container object *or* the contained object if it has
            been overridden via :meth:`override`.
    """
    def __init__(self, cls: Type[DelayedValue], names: Names, wait_for_target: bool) -> None:
        self.attrs: Dict[str, DelayedValue] = {}

        if isinstance(names, str):
            names = [names]

        for name in names:
            t = cls(name, wait_for_target=wait_for_target)
            self.attrs[t.attrname] = t
            self.attrs[t.name] = t

    def get(self, name: str) -> CollectedValue:
        """
        Obtain the object associated with name

        Args:
            name: The attribute name associated with the :obj:`.DelayedValue`

        Returns:
            :obj:`object`: The underlying object associated with this name.

        Raises:
            :obj:`NameError`: The name does not exist.
            :obj:`.DelayedAttributeError`: The name exists but the value
                has not been resolved yet.
        """
        if name not in self.attrs:
            raise NameError(f"'{self.__class__}' object has no '{name}'")

        if self.attrs[name].value is not None:
            setattr(self, name, self.attrs[name].value)
            return self.attrs[name].value

        raise DelayedAttributeError(name)

    def override(self, name: str, value: CollectedValue) -> None:
        """
        Override the :obj:`.DelayedValue` stored in the collection

        At times it may be required to override the value kept in the
        collection.
        """
        if not name in self.attrs:
            raise RuntimeError(f"{name} is not part of this collection")

        self.attrs[name].value = value

    def __getitem__(self, name: str) -> Any:
        try:
            return self.get(name)
        except NameError as e:
            raise KeyError(str(e)) from None

    def __getattr__(self, name: str) -> Any:
        try:
            return self.get(name)
        except NameError as e:
            raise AttributeError(str(e)) from None

class Types(DelayedCollection):
    """
    A container to resolve :obj:`gdb.Type` objects from the symbol table
    as they become available.

    Example:

    .. code-block:: pycon

        >>> from crash.util.symbols import Types
        >>> types = Types(["struct foo", "struct foo *"])
        >>> ex1 = types.foo_type
        >>> ex2 = types.foo_p_type
        >>> ex3 = types['foo_type']
        >>> ex4 = types['struct foo']

    See :meth:`~crash.infra.lookup.TypeCallback.resolve_type` for details.

    Args:
        names: A :obj:`str` or :obj:`list` of :obj:`str` containing the names
            of the types to resolve.
    """
    def __init__(self, names: Names, wait_for_target: bool = True) -> None:
        super(Types, self).__init__(DelayedType, names, wait_for_target)

    def override(self, name: str, value: gdb.Type) -> None: # type: ignore
        """
        Override the type value, resolving the type name first.

        The *real* type name is used, not the attribute name.

        .. code-block: pycon

        >>> t = gdb.lookup_type('struct foo')
        >>> types.override('struct foo', t)
        """
        # pylint: disable=unused-variable
        (name, attrname, pointer) = TypeCallback.resolve_type(name)

        super().override(name, value)
        super().override(attrname, value)

class Symbols(DelayedCollection):
    """
    A container to resolve :obj:`gdb.Symbol` objects from the symbol table
    as they become available.

    Example:

    .. code-block:: pycon

        >>> from crash.util.symbols import Symvals
        >>> symbols = Symbols(["modules", "super_blocks"])
        >>> print(symbols.modules)
        modules
        >>> print(symbols['modules'])
        modules
        >>> print(symbols.modules.type)
        <class 'gdb.Symbol'>

    Args:
        names: A :obj:`str` or :obj:`list` of :obj:`str` containing the names
            of the symbols to resolve.
    """
    def __init__(self, names: Names, wait_for_target: bool = True) -> None:
        super(Symbols, self).__init__(DelayedSymbol, names, wait_for_target)

class Symvals(DelayedCollection):
    """
    A container to resolve :obj:`gdb.Symbol` objects from the symbol table
    as they become available and use the associated values as the stored
    object.

    Example:

    .. code-block:: pycon

        >>> from crash.util.symbols import Symvals
        >>> symvals = Symvals(["modules", "super_blocks"])
        >>> print(symvals.modules)
        {
          next = 0xffffffffc0675208 <__this_module+8>,
          prev = 0xffffffffc00e8b48 <__this_module+8>
        }
        >>> print(symvals.modules.address)
        0xffffffffab0ff030 <modules>
        >>> print(symvals['modules'])
        {
          next = 0xffffffffc0675208 <__this_module+8>,
          prev = 0xffffffffc00e8b48 <__this_module+8>
        }
        >>> print(symvals.modules.type)
        <class 'gdb.Value'>

    Args:
        names: A :obj:`str` or :obj:`list` of :obj:`str` containing the names
            of the symbols to resolve.
    """
    def __init__(self, names: Names, wait_for_target: bool = True) -> None:
        super(Symvals, self).__init__(DelayedSymval, names, wait_for_target)

class MinimalSymbols(DelayedCollection):
    """
    A container to resolve :obj:`gdb.MinSymbol` objects from the symbol table
    as they become available.  Minimal symbols don't have any type information
    associated with them so they are mostly used to resolve names to
    addresses.

    Example:

    .. code-block:: pycon

    >>> import gdb
    >>> from crash.util.symbols import MinimalSymbols
    >>> msymbols = MinimalSymbols(['modules', 'super_block'])
    >>> print(msymbols.modules.type)
    11
    >>> print(gdb.MINSYMBOL_TYPE_FILE_BSS)
    11
    >>> print(msymbols['modules'])
    modules
    >>> print(msymbols['modules'].value())
    <data variable, no debug info>
    >>> print(msymbols['modules'].value().address)
    0xffffffff820ff030 <modules>
    >>> print(type(msymbols['modules']))
    <class 'gdb.MinSymbol'>

    Args:
        names: A :obj:`str` or :obj:`list` of :obj:`str` containing the names
            of the minimal symbols to resolve.
    """
    def __init__(self, names: Names, wait_for_target: bool = True) -> None:
        super().__init__(DelayedMinimalSymbol, names, wait_for_target)

class MinimalSymvals(DelayedCollection):
    """
    A container to resolve :obj:`gdb.MinSymbol` objects from the symbol table
    as they become available and uses the address of the values associated
    with them as the stored object.  Minimal symbols don't have any type
    information associated with them so they are mostly used to resolve
    names to addresses.

    Example:

    .. code-block:: pycon

    >>> import gdb
    from crash.util.symbols import MinimalSymvals
    >>> msymvals = MinimalSymvals(['modules', 'super_block'])
    >>> print(f"{msymvals.modules:#x}")
    0xffffffff820ff030
    >>> print(f"{msymvals['modules']:#x}")
    0xffffffff820ff030
    >>> print(type(msymvals['modules']))
    <class 'int'>

    Args:
        names: A :obj:`str` or :obj:`list` of :obj:`str` containing the names
            of the minimal symbols to resolve.
    """
    def __init__(self, names: Names, wait_for_target: bool = True) -> None:
        super().__init__(DelayedMinimalSymval, names, wait_for_target)

class DelayedValues(DelayedCollection):
    """
    A container to keep generic :class:`.DelayedValue` objects.

    These will raise :obj:`.DelayedAttributeError` until
    :meth:`.DelayedValue.callback` is called with a value to populate it.

    The callback must be accessed via :attr:`.DelayedCollection.attrs` or the
    :obj:`.DelayedValue` object will be evaluated first, also raising
    :obj:`.DelayedAttributeError`.

    Example:

    .. code-block:: pycon

    >>> from crash.util.symbols import DelayedValues
    >>> dvals = DelayedValues(['generic_value', 'another_value'])
    >>> dvals.attrs['generic_value'].callback(True)
    >>> print(dvals.generic_value)
    True
    >>> print(dvals.another_value)
    Traceback (most recent call last):
      File "<string>", line 4, in <module>
      File "./build/lib/crash/util/symbols.py", line 107, in __getattr__
        return self.get(name)
      File "./build/lib/crash/util/symbols.py", line 85, in get
        raise DelayedAttributeError(name)
    crash.exceptions.DelayedAttributeError: Delayed attribute another_value has not been completed.

    Args:
        names: The names to use for the :obj:`.DelayedValue` objects.
    """
    def __init__(self, names: Names, wait_for_target: bool = True) -> None:
        super().__init__(DelayedValue, names, wait_for_target)

CallbackSpecifier = Tuple[str, Callable]
CallbackSpecifiers = Union[List[CallbackSpecifier], CallbackSpecifier]

class CallbackCollection:
    def __init__(self, cls: Type[NamedCallback], cbs: CallbackSpecifiers,
                 wait_for_target: bool) -> None:
        if isinstance(cbs, tuple):
            cbs = [cbs]

        for cb in cbs:
            t = cls(cb[0], cb[1], wait_for_target=wait_for_target)
            setattr(self, t.attrname, t)

class TypeCallbacks(CallbackCollection):
    def __init__(self, cbs: CallbackSpecifiers, wait_for_target: bool = True) -> None:
        super().__init__(TypeCallback, cbs, wait_for_target)

class SymbolCallbacks(CallbackCollection):
    def __init__(self, cbs: CallbackSpecifiers, wait_for_target: bool = True) -> None:
        super().__init__(SymbolCallback, cbs, wait_for_target)

class MinimalSymbolCallbacks(CallbackCollection):
    def __init__(self, cbs: CallbackSpecifiers, wait_for_target: bool = True) -> None:
        super().__init__(MinimalSymbolCallback, cbs, wait_for_target)
