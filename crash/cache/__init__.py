# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import os
import glob
import importlib

from crash.infra import autoload_submodules

import gdb

class CrashCache:
    def refresh(self) -> None:
        pass

    def needs_updating(self) -> bool:
        return False

def discover() -> None:
    autoload_submodules('crash.cache')
