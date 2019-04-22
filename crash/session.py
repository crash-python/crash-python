# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import sys

from crash.infra import autoload_submodules
import crash.kernel
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

        self.kernel.setup_tasks()
        self.kernel.load_modules(searchpath)

