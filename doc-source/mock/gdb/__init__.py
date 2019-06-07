# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

class Target(object):
    class kdump(object):
        pass
        def get_addrxlat_ctx():
            pass
        class get_addrxlat_sys():
            def get_map(self, x):
                return []

class Register(object):
    pass

class Type(object):
    def __init__(self, x):
        pass

    @staticmethod
    def pointer():
        pass

class MinimalSymbol(object):
    section = None

class Symbol(object):
    section = None

class Inferior(object):
    new_thread = None

class InferiorThread(object):
    pass

class MinSymbol(object):
    pass

class Value(object):
    pass

class Objfile(object):
    architecture = None
    pass

def lookup_symbol(x, y):
    pass

def lookup_type(x):
    return Type(x)

class events(object):
    class new_objfile(object):
        def connect(x):
            pass

def objfiles():
    return []

def current_target():
    return Target()

class Block(object):
    pass

class Command(object):
    def __init__(self, x, y):
        pass

class NewObjFileEvent(object):
    pass

class Frame(object):
    pass

SYMBOL_VAR_DOMAIN = 0
COMMAND_USER = 0
