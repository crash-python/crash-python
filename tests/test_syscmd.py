# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb

from crash.exceptions import MissingSymbolError
from crash.commands import CrashCommandLineError
from crash.commands.syscmd import SysCommand

class TestSysCmd(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-syscache", to_string=True)
        self.cmd = SysCommand("pysys")

    def test_sys(self):
        self.cmd.invoke_uncaught("", from_tty=False)

    def test_sys_garbage(self):
        with self.assertRaises(CrashCommandLineError):
            self.cmd.invoke_uncaught("garbage", from_tty=False)

    def test_sys_garbage_flag(self):
        with self.assertRaises(CrashCommandLineError):
            self.cmd.invoke_uncaught("-a", from_tty=False)

    # This needs to be fixed when we have real vmcore testing
    def test_sys_config(self):
        with self.assertRaises(MissingSymbolError):
            self.cmd.invoke_uncaught("config", from_tty=False)
