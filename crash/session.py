# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import sys

from crash.infra import autoload_submodules
from crash.kernel import CrashKernel, CrashKernelError

class Session(object):
    """
    crash.Session is the main driver component for crash-python

    The Session class loads the kernel modules, sets up tasks, and auto loads
    any sub modules for autoinitializing commands and subsystems.

    Args:
        kernel (CrashKernel): The kernel to debug during this session
        verbose (bool, optional, default=False): Whether to enable verbose
            output
        debug (bool, optional, default=False): Whether to enable verbose
            debugging output
    """
    def __init__(self, kernel: CrashKernel, verbose: bool = False,
                 debug: bool = False) -> None:
        print("crash-python initializing...")
        self.kernel = kernel

        autoload_submodules('crash.cache')
        autoload_submodules('crash.subsystem')
        autoload_submodules('crash.commands')

        try:
            self.kernel.setup_tasks()
            self.kernel.load_modules(verbose=verbose, debug=debug)
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
