# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import os
import glob
import importlib

from crash.infra import autoload_submodules

import gdb

class CrashCache(object):
    def refresh(self):
        pass

    def needs_updating(self):
        return False

def discover():
    autoload_submodules('crash.cache')
