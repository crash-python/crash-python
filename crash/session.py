# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import List, Union

import gdb

from crash.infra import autoload_submodules
import crash.target
import crash.target.ppc64
import crash.target.x86_64

PathSpecifier = Union[List[str], str]

class Session:
    """
    crash.Session is the main driver component for crash-python

    The Session class loads the kernel modules, sets up tasks, and auto loads
    any sub modules for autoinitializing commands and subsystems.

    Args:
        kernel: The kernel to debug during this session
        verbose (optional, default=False): Whether to enable verbose
            output
        debug (optional, default=False): Whether to enable verbose
            debugging output
    """
    def __init__(self, roots: PathSpecifier = None,
                 vmlinux_debuginfo: PathSpecifier = None,
                 module_path: PathSpecifier = None,
                 module_debuginfo_path: PathSpecifier = None,
                 verbose: bool = False, debug: bool = False) -> None:
        print("crash-python initializing...")

        self.debug = debug
        self.verbose = verbose

        try:
            target = crash.target.setup_target()
        except crash.target.IncorrectTargetError as e:
            print(str(e))
            print("Further debugging may not be possible.")
            return

        from crash.kernel import CrashKernel, CrashKernelError

        self.kernel = CrashKernel(roots, vmlinux_debuginfo, module_path,
                                  module_debuginfo_path, verbose, debug)

        autoload_submodules('crash.cache')
        autoload_submodules('crash.subsystem')
        autoload_submodules('crash.commands')

        try:
            print("Loading modules")
            self.kernel.load_modules(verbose=verbose, debug=debug)
        except CrashKernelError as e:
            print(str(e))
            print("Further debugging may not be possible.")
            return

        if target.crashing_thread:
            try:
                result = gdb.execute("thread {}"
                                     .format(target.crashing_thread.num),
                                     to_string=True)
                if debug:
                    print(result)
            except gdb.error as e:
                print("Error while switching to crashed thread: {}"
                      .format(str(e)))
                print("Further debugging may not be possible.")
                return

            print("Backtrace from crashing task (PID {:d}):"
                  .format(target.crashing_thread.ptid[1]))
            gdb.execute("where")
