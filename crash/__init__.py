#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import crash.commands

class Session:
    def __init__(self, filename):
        import crash.kdump.target
        self.target = crash.kdump.target.Target(filename)
        crash.commands.discover()
