# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys

class wrap_method(object):
    """This pairs a function with an instance or class for calling
       from an unqualified context."""
    def __init__(self, method, cls):
        self.method = method
        self.cls = cls

    def __call__(self, *args, **kwargs):
        method = self.method
        return method(self.cls, *args, **kwargs)

def exporter(cls):
    """This marks the class for export to the module namespace.
       Individual methods must be exported with @export.
       Use of this decorator implies that this class will only have
       a single instance and the name of this class will refer to
       that instance.  It is possible to instantiate more copies
       using __class__ tricks.  Don't do that."""
    instance = cls()
    mod = sys.modules[cls.__module__]

    # inspect.getmembers plays tricks with static/classmethods
    for name, method in list(cls.__dict__.items()):
        # Staticmethods can be assigned directly
        if (type(method) is staticmethod and
            hasattr(method.__func__, '__export_to_module')):
            setattr(mod, name, method.__func__)
        elif (type(method) is classmethod and
              hasattr(method.__func__, "__export_to_module")):
                setattr(mod, name,
                        wrap_method(method.__func__, instance.__class__))
        elif hasattr(method, "__export_to_module"):
            setattr(mod, name, wrap_method(method, instance))
    return instance

def export(func):
    """This marks the function for export to the module namespace.
       The class must be decorated with @exporter."""
    if type(func) is staticmethod or type(func) is classmethod:
        func.__func__.__export_to_module = True
    else:
        func.__export_to_module = True
    return func

def __delayed_init__(self, *args, **kwargs):
    self.__initializing = True
    self.__init_args = args
    self.__init_kwargs = kwargs

def __getattr__(self, name):
    # call module.__init__ after import introspection is done
    if self.__initializing and not name[:2] == '__' == name[-2:]:
        self.__initializing = False
        self.__delayed_init__(*self.__init_args, **self.__init_kwargs)
    if name in self.__dict__:
        return getattr(self, name)

def delayed_init(self):
    """Decoration to delay class's __init__ until first access."""
    self.__delayed_init__ = self.__init__
    try:
        self.__real_getattr__ = self.__getattr__
    except AttributeError as e:
        self.__getattr__ = getattr
    self.__init__ = __delayed_init__
    self.__getattr__ = __getattr__
    return self
