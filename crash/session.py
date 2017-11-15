# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gdb
import sys

from crash.infra import autoload_submodules
from crash.kernel import load_debuginfo, load_modules
import crash.kdump.target
from kdumpfile import kdumpfile

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

        self.searchpath = searchpath

        if not kernel_exec:
            return

        error = gdb.execute("file {}".format(kernel_exec), to_string=True)

        try:
            list_type = gdb.lookup_type('struct list_head')
        except gdb.error as e:
            load_debuginfo(searchpath, gdb.objfiles()[0], kernelpath)
            try:
                list_type = gdb.lookup_type('struct list_head')
            except gdb.error as e:
                raise RuntimeError("Couldn't locate debuginfo for {}".format(kernel_exec))

        try:
            kdump = kdumpfile(vmcore)
        except OSErrorException as e:
            raise RuntimeError(str(e))

        self.target = crash.kdump.target.Target(kdump, debug)
        load_modules(self.searchpath)
