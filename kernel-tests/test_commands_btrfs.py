# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from decorators import skip_without_supers, skip_with_supers, skip_without_type

from crash.commands.btrfs import BtrfsCommand
from crash.commands import CommandLineError
from crash.exceptions import DelayedAttributeError

class TestCommandsBtrfs(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        self.redirected = io.StringIO()
        sys.stdout = self.redirected
        self.command = BtrfsCommand("btrfs")

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return self.redirected.getvalue()

    def output_lines(self):
        output = self.output()
        return len(output.split("\n")) - 1

    def test_btrfs_empty(self):
        """`btrfs` raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("")

    @skip_without_supers('btrfs')
    def test_btrfs_list(self):
        """`btrfs list` produces valid output"""
        self.command.invoke_uncaught("list")
        self.assertTrue(self.output_lines() > 0)

    @skip_without_supers('btrfs')
    def test_btrfs_list_m(self):
        """`btrfs list -m` produces valid output"""
        self.command.invoke_uncaught("list -m")
        self.assertTrue(self.output_lines() > 0)

    @skip_with_supers('btrfs')
    def test_btrfs_list_without_supers(self):
        """`btrfs list` without supers produces one-line status"""
        self.command.invoke_uncaught("list")
        self.assertTrue(self.output_lines() == 1)

    @skip_with_supers('btrfs')
    def test_btrfs_list_m_without_supers(self):
        """`btrfs list -m` without supers produces one-line status"""
        self.command.invoke_uncaught("list -m")
        self.assertTrue(self.output_lines() == 1)

    def test_btrfs_list_invalid(self):
        """`btrfs list -invalid` raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("list -invalid")

    def test_btrfs_invalid_command(self):
        """`btrfs invalid command` raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("invalid command")
