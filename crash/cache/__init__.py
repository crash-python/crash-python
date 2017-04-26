# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb

import os
import glob
import importlib

from crash.infra import CrashBaseClass

class CrashCache(CrashBaseClass):
    def refresh(self):
        pass

    def needs_updating(self):
        return False

def discover():
    modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
    __all__ = [os.path.basename(f)[:-3] for f in modules]

    mods = __all__
    for mod in mods:
        x = importlib.import_module("crash.cache.{}".format(mod))
