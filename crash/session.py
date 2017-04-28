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

class Session(object):
    """crash.Session is the main driver component for crash-python"""
    def __init__(self, kernel_exec, vmcore, kernelpath, searchpath=None,
                 debug=False):
        print("crash-python initializing...")
        if searchpath is None:
            searchpath = []

        self.searchpath = searchpath

        error = gdb.execute("file {}".format(kernel_exec), to_string=True)

        try:
            list_type = gdb.lookup_type('struct list_head')
        except gdb.error as e:
            load_debuginfo(searchpath, gdb.objfiles()[0], kernelpath)
            try:
                list_type = gdb.lookup_type('struct list_head')
            except gdb.error as e:
                raise RuntimeError("Couldn't locate debuginfo for {}".format(kernel_exec))

        self.target = crash.kdump.target.Target(vmcore, debug)
        load_modules(self.searchpath)
        autoload_submodules('crash.cache')
        autoload_submodules('crash.commands')
