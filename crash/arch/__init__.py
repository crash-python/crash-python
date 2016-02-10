#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import os
import glob
import importlib

class CrashArchitecture:
    ident = "base-class"
    aliases = None
    def __init__(self):
        pass

    def setup_thread(self, thread):
        raise NotImplementedError("setup_thread not implemented")

architectures = {}
def register(arch):
    architectures[arch.ident] = arch
    for ident in arch.aliases:
        architectures[ident] = arch

def get_architecture(archname):
    if archname in architectures:
        return architectures[archname]

    return None

modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
__all__ = [ os.path.basename(f)[:-3] for f in modules]

mods = __all__
for mod in mods:
    x = importlib.import_module("crash.arch.%s" % mod)
