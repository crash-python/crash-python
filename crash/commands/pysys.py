#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import gdb
from crash.commands import CrashCommand
from crash.cache import sysinfo
import argparse

class LogTypeException(Exception):
    pass

class LogInvalidOption(Exception):
    pass

class SysCommand(CrashCommand):
    """system data

NAME
  sys - system data

SYNOPSIS
  sys [config]

DESCRIPTION
  This command displays system-specific data. If no arguments are entered,
  the same system data shown during crash invocation is shown.

    config            If the kernel was configured with CONFIG_IKCONFIG, then
                      dump the in-kernel configuration data.

EXAMPLES
  Display essential system information:

    crash> sys config
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

        parser = argparse.ArgumentParser(prog=name)

        parser.add_argument('config', nargs='?')

        parser.format_usage = lambda : "sys [config]\n"
        CrashCommand.__init__(self, name, parser)


    def show_default(self):
        print("      UPTIME: %s" % (sysinfo.cache.kernel_cache['uptime']))
        print("LOAD AVERAGE: %s" % (sysinfo.cache.kernel_cache['loadavg']))
        print("    NODENAME: %s" % (sysinfo.cache.utsname_cache['nodename']))
        print("     RELEASE: %s" % (sysinfo.cache.utsname_cache['release']))
        print("     VERSION: %s" % (sysinfo.cache.utsname_cache['version']))
        print("     MACHINE: %s" % (sysinfo.cache.utsname_cache['machine']))

    def show_raw_ikconfig(self):
        print(sysinfo.cache.ikconfig_raw_cache)

    def execute(self, args):
        sysinfo.cache.init_sys_caches()

        if args.config:
            if args.config == "config":
                self.show_raw_ikconfig()
            else:
                print("Error: unknown option: %s" % (args.config))
        else:
            self.show_default()

SysCommand("sys")
