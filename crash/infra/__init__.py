# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Callable, Any, List

import sys
import glob
import os.path
import importlib

def autoload_submodules(caller: str,
                        callback: Callable[[Any], None] = None) -> List[str]:
    mods = []
    try:
        mod = sys.modules[caller]
    except KeyError:
        mod = importlib.import_module(caller)
        mods.append(caller)
    if mod.__file__ is None:
        return list()
    path = os.path.dirname(mod.__file__)
    modules = glob.glob("{}/[A-Za-z0-9_]*.py".format(path))
    for modname in modules:
        modname = os.path.basename(modname)[:-3]
        if modname == '__init__':
            continue
        modname = "{}.{}".format(caller, modname)
        x = importlib.import_module(modname)
        if callback:
            callback(x)
        mods.append(modname)
    packages = glob.glob("{}/[A-Za-z0-9_]*/__init__.py".format(path))
    for pkg in packages:
        modname = "{}.{}".format(caller, os.path.basename(os.path.dirname(pkg)))
        x = importlib.import_module(modname)
        if callback:
            callback(x)

        mods += autoload_submodules(modname, callback)
    return mods
