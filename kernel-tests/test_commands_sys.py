# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from crash.commands.syscmd import SysCommand

class TestCommandsSys(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        self.redirect = io.StringIO()
        sys.stdout = self.redirect
        self.command = SysCommand("sys")

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return self.redirect.getvalue()

    def output_lines(self):
        return len(self.output().split("\n"))

    def test_sys(self):
        self.command.invoke_uncaught("")
        self.assertTrue(self.output_lines() > 2)

    def test_sys_config(self):
        self.command.invoke_uncaught("config")
        self.assertTrue(self.output_lines() > 2)
