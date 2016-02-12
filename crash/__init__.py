#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import kdump.target
import crash.commands

class Session:
    def __init__(self, filename):
        self.target = kdump.target.Target(filename)
