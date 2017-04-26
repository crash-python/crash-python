# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from future.utils import with_metaclass

import sys
import inspect

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

def export(func):
    """This marks the function for export to the module namespace.
       The class must inherit from CrashBaseClass."""
    if isinstance(func, staticmethod) or isinstance(func, classmethod):
        func.__func__.__export_to_module__ = True
    else:
        func.__export_to_module__ = True
    return func

def delayed_init(cls):
    """This marks a class for delayed initialization.  It is implemented
    by inheriting from the base class and wraps it with separate
    __init__, __getattr__, and __setattr__ routines.

    There is one big limitation: super() can't be used since it will
    return the base class instead of a parent of the base class.  If
    super().__init__ is called from base_class.__init__ it will result
    in infinite recursion."""
    if not isinstance(cls, type):
        raise TypeError("must be class not instance")
    class delayed_init_class(cls):
        def __init__(self, *args, **kwargs):
            self.__dict__['__initializing'] = True
            self.__dict__['__init_args'] = args
            self.__dict__['__init_kwargs'] = kwargs
            self.__dict__['__cls'] = cls

        def __delayed_init__(self):
            cls = self.__dict__['__cls']
            args = self.__dict__['__init_args']
            kwargs = self.__dict__['__init_kwargs']
            cls.__init__(self, *args, **kwargs)

        def __setattr__(self, name, value):
            if (self.__dict__['__initializing'] and
                    not name[:2] == '__' == name[-2:]):
                self.__dict__['__initializing'] = False
                self.__delayed_init__()

            cls = self.__dict__['__cls']
            return cls.__setattr__(self, name, value)

        def __getattr__(self, name):
            if (self.__dict__['__initializing'] and
                    not name[:2] == '__' == name[-2:]):
                self.__dict__['__initializing'] = False
                self.__delayed_init__()
                return getattr(self, name)
            cls = self.__dict__['__cls']
            if hasattr(cls, '__getattr__'):
                return cls.__getattr__(self, name)
            raise AttributeError('type {} does not contain attribute {}'.format(type(self), name))

    delayed_init_class.__name__ = "{}_delayed".format(cls.__name__)
    delayed_init_class.wrapped_class = cls
    return delayed_init_class

class _CrashBaseMeta(type):
    """This metaclass handles both exporting methods to the module namespace
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
