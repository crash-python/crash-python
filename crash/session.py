# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import sys

from crash.infra import autoload_submodules
import crash.kernel
from crash.kernel import CrashKernelError
from kdumpfile import kdumpfile

class Session(object):
    """
    crash.Session is the main driver component for crash-python

    The Session class loads the kernel, kernel modules, debuginfo,
    and vmcore and auto loads any sub modules for autoinitializing
    commands and subsystems.

    Args:
        searchpath (list of str, optional): Paths to directory trees to
            search for kernel modules and debuginfo
        debug (bool, optional, default=False): Whether to enable verbose
            debugging output
    """


    def __init__(self, searchpath=None, debug=False):
        print("crash-python initializing...")
        if searchpath is None:
            searchpath = []

        self.kernel = crash.kernel.CrashKernel(searchpath)

        autoload_submodules('crash.cache')
        autoload_submodules('crash.subsystem')
        autoload_submodules('crash.commands')

        try:
            self.kernel.setup_tasks()
            self.kernel.load_modules(searchpath)
        except CrashKernelError as e:
            print(str(e))
            print("Further debugging may not be possible.")
            return

        if self.kernel.crashing_thread:
            try:
                result = gdb.execute("thread {}"
                                      .format(self.kernel.crashing_thread.num),
                                     to_string=True)
                if debug:
                    print(result)
            except gdb.error as e:
                print("Error while switching to crashed thread: {}"
                                                                .format(str(e)))
                print("Further debugging may not be possible.")
                return

            print("Backtrace from crashing task (PID {:d}):"
                  .format(self.kernel.crashing_thread.ptid[1]))
            gdb.execute("where")
