# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from decorators import skip_without_supers, skip_with_supers

from crash.commands.xfs import XFSCommand
from crash.exceptions import DelayedAttributeError
from crash.commands import CommandLineError, CommandError

class TestCommandsXFS(unittest.TestCase):
    """
    These tests require that the xfs file system be built-in or loaded as
    a module.  If the test vmcore doesn't have the xfs module loaded or
    modules haven't been provided, most of these tests will be skipped.
    """

    def setUp(self):
        self.stdout = sys.stdout
        self.redirected = io.StringIO()
        sys.stdout = self.redirected
        self.command = XFSCommand("xfs")

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return self.redirected.getvalue()

    def output_lines(self):
        return len(self.output().split("\n")) - 1

    def test_empty_command(self):
        """`xfs' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("")

    def test_invalid_command(self):
        """`xfs invalid command' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("invalid command")

    @skip_without_supers('xfs')
    def test_xfs_list(self):
        """`xfs list' produces valid output"""
        self.command.invoke_uncaught("list")
        self.assertTrue(self.output_lines() > 0)

    @skip_with_supers('xfs')
    def test_xfs_list_no_mounts(self):
        """`xfs list' produces one-line status with no mounts"""
        self.command.invoke_uncaught("list")
        self.assertTrue(self.output_lines() == 1)

    def test_xfs_list_invalid(self):
        """`xfs list invalid' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("list invalid")

    def test_xfs_show_null(self):
        """`xfs show 0' raises CommandError"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("show 0")

    def test_xfs_dump_ail_null(self):
        """`xfs dump-ail 0' raises CommandError"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("dump-ail 0")

    def test_xfs_dump_buft_null(self):
        """`xfs dump-buft 0' raises CommandError"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("dump-buft 0")

