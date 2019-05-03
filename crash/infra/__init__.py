# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import sys
import glob
import os.path
import importlib

def autoload_submodules(caller, callback=None):
    mods = []
    try:
        mod = sys.modules[caller]
    except KeyError:
        mod = importlib.import_module(caller)
        mods.append(caller)
    path = os.path.dirname(mod.__file__)
    modules = glob.glob("{}/[A-Za-z0-9_]*.py".format(path))
    for mod in modules:
        mod = os.path.basename(mod)[:-3]
        if mod == '__init__':
            continue
        modname = "{}.{}".format(caller, mod)
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
