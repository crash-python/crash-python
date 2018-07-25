# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gdb
import sys

from crash.infra import autoload_submodules
import crash.kernel

class Session(object):
    """crash.Session is the main driver component for crash-python"""
    def __init__(self, kernel_exec=None, vmcore=None, kernelpath=None,
                 searchpath=None, debug=False):
        print("crash-python initializing...")
        if searchpath is None:
            searchpath = []

        autoload_submodules('crash.cache')
        autoload_submodules('crash.subsystem')
        autoload_submodules('crash.commands')

        if not kernel_exec:
            return

        self.kernel = crash.kernel.CrashKernel(kernel_exec, searchpath)
        self.kernel.attach_vmcore(vmcore, debug)
        self.kernel.setup_tasks()
        self.kernel.load_modules(searchpath)
