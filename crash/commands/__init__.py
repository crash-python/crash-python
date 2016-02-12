# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb

import os
import glob
import importlib

class CrashCommand(gdb.Command):
    def __init__(self, name, parser):
        gdb.Command.__init__(self, "py" + name, gdb.COMMAND_USER)
        parser.format_help = lambda: self.__doc__
        self.parser = parser

    def invoke(self, argstr, from_tty):
        argv = gdb.string_to_argv(argstr)
        try:
            args = self.parser.parse_args(argv)
            self.execute(args)
        except SystemExit:
            return
        except KeyboardInterrupt:
            return

    def execute(self, argv):
        raise NotImplementedError("CrashCommand should not be called directly")

def discover():
    modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
    __all__ = [os.path.basename(f)[:-3] for f in modules]

    mods = __all__
    for mod in mods:
        x = importlib.import_module("crash.commands.{}".format(mod))
