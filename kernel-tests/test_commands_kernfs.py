# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys


from crash.commands.kernfs import KernfsCommand
from crash.commands import CommandLineError

class TestCommandsKernfs(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        self.redirected = io.StringIO()
        sys.stdout = self.redirected
        self.command = KernfsCommand("kernfs")
        self.kn_addr = int(gdb.lookup_symbol('sysfs_root_kn', None)[0].value())

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return self.redirected.getvalue()

    def output_lines(self):
        output = self.output()
        return len(output.split("\n")) - 1

    def test_kernfs_empty(self):
        """`kernfs` raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("")

    def test_kernfs_list(self):
        """`kernfs ls` produces valid output"""
        self.command.invoke_uncaught(f"ls {self.kn_addr:x}")
        # header + listing
        self.assertTrue(self.output_lines() > 1)

    def test_kernfs_list_recursive(self):
        """`kernfs ls` produces valid output"""
        self.command.invoke_uncaught(f"ls -R 2 {self.kn_addr:x}")
        # header + listing
        self.assertTrue(self.output_lines() > 1)
