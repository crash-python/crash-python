# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from future.utils import with_metaclass

import sys
import glob
import os.path
import inspect
import importlib

from crash.infra.lookup import DelayedLookups

class export_wrapper(object):
    def __init__(self, mod, cls, func):
        self.cls = cls
        self.func = func

        if not hasattr(mod, '_export_wrapper_singleton_dict'):
            mod._export_wrapper_singleton_dict = {}
        self.singleton_dict = mod._export_wrapper_singleton_dict

    def __call__(self, *args, **kwargs):
        try:
            obj = self.singleton_dict[self.cls]
        except KeyError:
            obj = self.cls()
            self.singleton_dict[self.cls] = obj

        if isinstance(self.func, classmethod):
            return self.func.__func__(self.cls, *args, **kwargs)
        elif isinstance(self.func, staticmethod):
            return self.func.__func__(*args, **kwargs)
        else:
            return self.func(obj, *args, **kwargs)

def register_singleton(mod, obj):
    if not hasattr(mod, '_export_wrapper_singleton_dict'):
        raise RuntimeError("Class {} has no exported members."
                            .format(obj.__class__.__name__))

    mod._export_wrapper_singleton_dict[obj.__class__] = obj

def export(func):
    """This marks the function for export to the module namespace.
       The class must inherit from CrashBaseClass."""
    if isinstance(func, staticmethod) or isinstance(func, classmethod):
        func.__func__.__export_to_module__ = True
    else:
        func.__export_to_module__ = True
    return func

class _CrashBaseMeta(type):
    """
    This metaclass handles both exporting methods to the module namespace
    and handling asynchronous loading of types and symbols.  To enable it,
    all you need to do is define your class as follows:

    class Foo(CrashBaseClass):
        ...

    There are several special class variables that are interpreted during
    class (not instance) creation.

    The following create properties in the class that initially
    raise MissingSymbolError but contain the requested information when
    made available.  The properties for types will be the name of the type,
    with 'struct ' removed and _type appended.  E.g. 'struct test' becomes
    test_type.  If it's a pointer type, _p is appended after the type name,
    e.g. 'struct test *' becomes test_p_type.  The properties for the symbols
    are named with the symbol name.  If there is a naming collision,
    NameError is raised.
    __types__      -- A list consisting of type names.  Pointer are handled in
                      Pointer are handled in a manner similarly to how
                      they are handled in C code. e.g. 'char *'.
    __symbols__    -- A list of symbol names
    __minsymbols__ -- A list of minimal symbols
    __symvals__    -- A list of symbol names that will return the value
                      associated with the symbol instead of the symbol itself.

    The following set up callbacks when the requested type or symbol value
    is available.  These each accept a list of 2-tuples, (specifier, callback).
    The callback is passed the type or symbol requested.
    __type_callbacks__
    __symbol_callbacks__
    """
    def __new__(cls, name, parents, dct):
        DelayedLookups.setup_delayed_lookups_for_class(name, dct)
        return type.__new__(cls, name, parents, dct)

    def __init__(cls, name, parents, dct):
        super(_CrashBaseMeta, cls).__init__(name, parents, dct)
        cls.setup_exports_for_class(cls, dct)
        DelayedLookups.setup_named_callbacks(cls, dct)

    @staticmethod
    def setup_exports_for_class(cls, dct):
        mod = sys.modules[dct['__module__']]
        for name, decl in dct.items():
            if (hasattr(decl, '__export_to_module__') or
                ((isinstance(decl, classmethod) or
                  isinstance(decl, staticmethod)) and
                 hasattr(decl.__func__, "__export_to_module__"))):
                setattr(mod, name, export_wrapper(mod, cls, decl))

class CrashBaseClass(with_metaclass(_CrashBaseMeta)):
    pass

def autoload_submodules(caller, callback=None):
    mods = []
    try:
        mod = sys.modules[caller]
    except KeyError:
        mod = importlib.import_module(caller)
        mods.append(caller)
    path = os.path.dirname(mod.__file__)
    modules = glob.glob("{}/[A-Za-z0-9_]*.py".format(path))
    for mod in modules:
        mod = os.path.basename(mod)[:-3]
        if mod == '__init__':
            continue
        modname = "{}.{}".format(caller, mod)
        x = importlib.import_module(modname)
        if callback:
            callback(x)
        mods.append(modname)
    packages = glob.glob("{}/[A-Za-z0-9_]*/__init__.py".format(path))
    for pkg in packages:
        modname = "{}.{}".format(caller, os.path.basename(os.path.dirname(pkg)))
        x = importlib.import_module(modname)
        if callback:
            callback(x)

        mods += autoload_submodules(modname, callback)
    return mods
