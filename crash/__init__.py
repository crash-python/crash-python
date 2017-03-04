#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:


class Session:
    def __init__(self, filename):
        import crash.kdump.target
        self.target = crash.kdump.target.Target(filename)
        import crash.commands
