# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

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
        kernel_exec (str, optional): The path to the kernel executable
        vmcore (str, optional): The path to the vmcore
        kernelpath (str, optional): The path the kernel name to use
            when reporting errors
        searchpath (list of str, optional): Paths to directory trees to
            search for kernel modules and debuginfo
        debug (bool, optional, default=False): Whether to enable verbose
            debugging output
    """


    def __init__(self, kernel_exec=None, vmcore=None, kernelpath=None,
                 searchpath=None, debug=False):
        self.vmcore_filename = vmcore

        print("crash-python initializing...")
        if searchpath is None:
            searchpath = []

        if kernel_exec:
            self.kernel = crash.kernel.CrashKernel(kernel_exec, searchpath)
            self.kernel.attach_vmcore(vmcore, debug)
            self.kernel.open_kernel()

        autoload_submodules('crash.cache')
        autoload_submodules('crash.subsystem')
        autoload_submodules('crash.commands')

        if kernel_exec:
            self.kernel.setup_tasks()
            self.kernel.load_modules(searchpath)


