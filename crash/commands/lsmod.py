# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Display module information

::

  lsmod [-p [n]] [name-wildcard]

DESCRIPTION
-----------

This command displays information about loaded modules.

The default output will show all loaded modules, the core address,
its size, and any users of the module.  By specifying [name-wildcard],
the results can be filtered to modules matching the wildcard.

The following options are available:

-p       display the percpu base for the module and the size of its region
-p CPU   display the percpu base for the module and the size of its region
         for the specified CPU number

"""

import re
import fnmatch
import argparse

import gdb

from crash.commands import Command, ArgumentParser
from crash.types.module import for_each_module
from crash.util import struct_has_member
from crash.util.symbols import Types
from crash.types.list import list_for_each_entry
from crash.types.percpu import get_percpu_var

types = Types(['struct module_use'])

class ModuleCommand(Command):
    """display module information"""

    def __init__(self) -> None:
        parser = ArgumentParser(prog="lsmod")

        parser.add_argument('-p', nargs='?', const=-1, default=None, type=int)
        parser.add_argument('args', nargs=argparse.REMAINDER)

        Command.__init__(self, "lsmod", parser)

    def print_module_percpu(self, mod: gdb.Value, cpu: int = -1) -> None:
        cpu = int(cpu)
        addr = int(mod['percpu'])
        if addr == 0:
            return

        if cpu != -1:
            addr = int(get_percpu_var(mod['percpu'], cpu))
            tabs = "\t\t"
        else:
            tabs = "\t\t\t"

        size = int(mod['percpu_size'])
        print("{:16s}\t{:#x}{}{:d}".format(mod['name'].string(), addr,
                                           tabs, size))


    def execute(self, args: argparse.Namespace) -> None:
        regex = None
        print_header = True
        if args.args:
            regex = re.compile(fnmatch.translate(args.args[0]))

        core_layout = None

        for mod in for_each_module():
            if core_layout is None:
                core_layout = struct_has_member(mod.type, 'core_layout')

            modname = mod['name'].string()
            if regex:
                m = regex.match(modname)
                if m is None:
                    continue

            if args.p is not None:
                if print_header:
                    print_header = False
                    if args.p == -1:
                        print("Module\t\t\tPercpu Base\t\tSize")
                    else:
                        print("Module\t\t\tPercpu Base@CPU{:d}\t\tSize"
                              .format(args.p))
                self.print_module_percpu(mod, args.p)
                continue

            if print_header:
                print_header = False
                print("Module\t\t\tAddress\t\t\tSize\tUsed by")

            if core_layout:
                addr = int(mod['core_layout']['base'])
                size = int(mod['core_layout']['size'])
            else:
                addr = int(mod['module_core'])
                size = int(mod['core_size'])

            module_use = ""
            count = 0
            for use in list_for_each_entry(mod['source_list'],
                                           types.module_use_type,
                                           'source_list'):
                if module_use == "":
                    module_use += " "
                else:
                    module_use += ","
                module_use += use['source']['name'].string()
                count += 1

            print("{:16s}\t{:#x}\t{:d}\t{:d}{}"
                  .format(modname, addr, size, count, module_use))

ModuleCommand()
