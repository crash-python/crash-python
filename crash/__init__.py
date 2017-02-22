#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from .kdump import target

class Session:
    def __init__(self, filename):
        self.target = kdump.target.Target(filename)
        import crash.commands
