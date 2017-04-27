# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
import inspect

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

def exporter(cls):
    """This marks the class for export to the module namespace.
       Individual methods must be exported with @export.

       The exported routines will share a single, private class
       instance."""

    # Detect delayed_init and use the right module
    if hasattr(cls, 'wrapped_class'):
        mod = sys.modules[cls.wrapped_class.__module__]
    else:
        mod = sys.modules[cls.__module__]
    for name, method in inspect.getmembers(cls):
        for superclass in cls.mro():
            if name in superclass.__dict__:
                decl = superclass.__dict__[name]
                break
        if (hasattr(decl, '__export_to_module__') or
            ((isinstance(decl, classmethod) or
              isinstance(decl, staticmethod)) and
             hasattr(decl.__func__, "__export_to_module__"))):
            setattr(mod, name, export_wrapper(mod, cls, decl))
    return cls

def export(func):
    """This marks the function for export to the module namespace.
       The class must be decorated with @exporter."""
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
