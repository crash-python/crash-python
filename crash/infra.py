# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
import inspect

def exporter(cls):
    """This marks the class for export to the module namespace.
       Individual methods must be exported with @export.
       Use of this decorator implies that this class will only have
       a single instance and the name of this class will refer to
       that instance.  It is possible to instantiate more copies
       using __class__ tricks.  Don't do that."""
    instance = cls()
    if hasattr(cls, 'wrapped_class'):
        mod = sys.modules[cls.wrapped_class.__module__]
    else:
        mod = sys.modules[cls.__module__]

    # If we use inspect.getmembers, we get everything but we also
    # get appropriately bound methods so we don't need to play wrapper
    # games.
    for name, method in inspect.getmembers(instance):
        for superclass in instance.__class__.mro():
            if name in superclass.__dict__:
                decl = superclass.__dict__[name]
                break
        if hasattr(method, "__export_to_module__"):
            setattr(mod, name, method)
    return instance

def export(func):
    """This marks the function for export to the module namespace.
       The class must be decorated with @exporter."""
    if isinstance(func, staticmethod) or isinstance(func, classmethod):
        func.__func__.__export_to_module__ = True
    else:
        func.__export_to_module__ = True
    return func

def delayed_init(cls):
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
