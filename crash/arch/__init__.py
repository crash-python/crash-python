#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

class CrashArchitecture(object):
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
