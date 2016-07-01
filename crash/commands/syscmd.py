# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from crash.commands import CrashCommand, CrashCommandParser
from crash.cache.syscache import utsname

class SysCommand(CrashCommand):
    """system data

NAME
  sys - system data

SYNOPSIS
  sys

DESCRIPTION
  This command displays system-specific data.

EXAMPLES
  Display essential system information:

    crash> sys
          KERNEL: vmlinux.4
        DUMPFILE: lcore.cr.4
            CPUS: 4
            DATE: Mon Oct 11 18:48:55 1999
          UPTIME: 10 days, 14:14:39
    LOAD AVERAGE: 0.74, 0.23, 0.08
           TASKS: 77
        NODENAME: test.mclinux.com
         RELEASE: 2.2.5-15smp
         VERSION: #24 SMP Mon Oct 11 17:41:40 CDT 1999
         MACHINE: i686  (500 MHz)
          MEMORY: 1 GB


    """
    def __init__(self, name):

        parser = CrashCommandParser(prog=name)

        parser.format_usage = lambda: "sys\n"
        CrashCommand.__init__(self, name, parser)

    @staticmethod
    def show_default():
        print("    NODENAME: {}".format(utsname.nodename))
        print("     RELEASE: {}".format(utsname.release))
        print("     VERSION: {}".format(utsname.version))
        print("     MACHINE: {}".format(utsname.machine))

    def execute(self, args):
        self.show_default()

SysCommand("sys")
