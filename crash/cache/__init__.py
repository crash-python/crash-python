# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

import os
import glob
import importlib

from crash.infra import autoload_submodules

class CrashCache(object):
    def refresh(self):
        pass

    def needs_updating(self):
        return False

def discover():
    autoload_submodules('crash.cache')
