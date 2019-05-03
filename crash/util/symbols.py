# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Type, List, Tuple, Callable, Union, Dict

import gdb

from crash.infra.lookup import DelayedType, DelayedSymbol, DelayedSymval
from crash.infra.lookup import DelayedValue, DelayedMinimalSymbol
from crash.infra.lookup import DelayedMinimalSymval
from crash.infra.lookup import NamedCallback, TypeCallback
from crash.infra.lookup import SymbolCallback, MinimalSymbolCallback
from crash.exceptions import DelayedAttributeError

CollectedValue = Union[gdb.Type, gdb.Value, gdb.Symbol, gdb.MinSymbol]

class DelayedCollection(object):
    def __init__(self, cls: Type[DelayedValue], names: Union[List[str,], str]):
        self.attrs: Dict[str, DelayedValue] = {}

        if isinstance(names, str):
            names = [ names ]

        for name in names:
            t = cls(name)
            self.attrs[t.attrname] = t

    def get(self, name):
        if name not in self.attrs:
            raise NameError(f"'{self.__class__}' object has no '{name}'")

        if self.attrs[name].value is not None:
            setattr(self, name, self.attrs[name].value)
            return self.attrs[name].value

        raise DelayedAttributeError(name)

    def override(self, name: str, value: CollectedValue):
        if not name in self.attrs:
            raise RuntimeError(f"{name} is not part of this collection")

        self.attrs[name].value = value

    def __getitem__(self, name):
        try:
            return self.get(name)
        except NameError as e:
            raise KeyError(str(e))

    def __getattr__(self, name):
        try:
            return self.get(name)
        except NameError as e:
            raise AttributeError(str(e))

class Types(DelayedCollection):
    def __init__(self, names):
        super(Types, self).__init__(DelayedType, names)

    def override(self, name, value):
        (ignore, name, pointer) = TypeCallback.resolve_type(name)

        super().override(name, value)

class Symbols(DelayedCollection):
    def __init__(self, names):
        super(Symbols, self).__init__(DelayedSymbol, names)

class Symvals(DelayedCollection):
    def __init__(self, names):
        super(Symvals, self).__init__(DelayedSymval, names)

class MinimalSymbols(DelayedCollection):
    def __init__(self, names):
        super(MinimalSymbols, self).__init__(DelayedMinimalSymbol, names)

class MinimalSymvals(DelayedCollection):
    def __init__(self, names):
        super(MinimalSymvals, self).__init__(DelayedMinimalSymval, names)

class DelayedValues(DelayedCollection):
    def __init__(self, names):
        super(DelayedValues, self).__init__(DelayedDelayedValue, names)

CallbackSpecifier = Tuple[str, Callable]
CallbackSpecifiers = Union[List[CallbackSpecifier], CallbackSpecifier]

class CallbackCollection(object):
    def __init__(self, cls: Type[NamedCallback], cbs: CallbackSpecifiers):
        if isinstance(cbs, tuple):
            cbs = [ cbs ]

        for cb in cbs:
            t = cls(cb[0], cb[1])
            setattr(self, t.attrname, t)

class TypeCallbacks(CallbackCollection):
    def __init__(self, cbs):
        super().__init__(TypeCallback, cbs)

class SymbolCallbacks(CallbackCollection):
    def __init__(self, cbs):
        super().__init__(SymbolCallback, cbs)

class MinimalSymbolCallbacks(CallbackCollection):
    def __init__(self, cbs):
        super().__init__(MinimalSymbolCallback, cbs)

