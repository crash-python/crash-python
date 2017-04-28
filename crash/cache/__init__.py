# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb

import os
import glob
import importlib

from crash.infra import CrashBaseClass, autoload_submodules

class CrashCache(CrashBaseClass):
    def refresh(self):
        pass

    def needs_updating(self):
        return False

def discover():
    autoload_submodules('crash.cache')
