#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import argparse
from crash.commands import CrashCommand
from crash.types.task import LinuxTask
from crash.types.list import list_for_each_entry

import os
import os.path
import fnmatch

class MODCommand(CrashCommand):
    """display modules information

    """
    def __init__(self):
        parser = argparse.ArgumentParser(prog="mod")

        group = parser.add_mutually_exclusive_group()
        parser.add_argument('-S', help='directory with debuginfo')
        parser.add_argument('args', nargs=argparse.REMAINDER)

        parser.format_usage = lambda : \
        "mod [-S path]\n"

        CrashCommand.__init__(self, "mod", parser)

    def execute(self, argv):

        if not argv.S:
            gdb.write("Give me -S path/to/debuginfo\n")
            return

        mods = {}
        for root, dirnames, filenames in os.walk(argv.S):
            for filename in fnmatch.filter(filenames, '*.ko.debug'):
                modname = os.path.basename(filename)[:-9] # strip that .ko.debug
                mods [modname] = os.path.join(root, filename)

        modules = gdb.lookup_symbol("modules", None)[0].value()
        t_module = gdb.lookup_type("struct module")

        for mod in list_for_each_entry(modules, t_module, 'list'):
            modname = mod["name"].string()
            module_core = long(mod["module_core"])
            if not mods.has_key(modname):
                gdb.write("Debuginfo for %s not found (to be loaded at %lx)!\n" % (modname, module_core))
            else:
                gdb.execute("add-symbol-file %s 0x%lx" % (mods[modname], module_core))

MODCommand()
