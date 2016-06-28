#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

import os
import glob
import importlib

class CrashCache(object):
    def __init__(self):
        pass

    def refresh(self):
        pass

    def needs_updating(self):
        return False

modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
__all__ = [ os.path.basename(f)[:-3] for f in modules]

mods = __all__
for mod in mods:
    x = importlib.import_module("crash.cache.%s" % mod)
