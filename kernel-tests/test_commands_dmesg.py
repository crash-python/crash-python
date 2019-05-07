# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from decorators import skip_with_symbol, skip_without_symbol

from crash.commands.dmesg import LogCommand
from crash.commands import CommandError, CommandLineError

class TestCommandsLog(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = io.StringIO()
        self.command = LogCommand("dmesg")

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return sys.stdout.getvalue()

    def test_dmesg(self):
        """`dmesg' produces valid output"""
        self.command.invoke_uncaught("")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_dmesg_bad_option(self):
        """`dmesg -x` raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-x")

    def test_dmesg_t(self):
        """`dmesg' produces valid output"""
        self.command.invoke_uncaught("-t")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    @skip_without_symbol('log_first_seq')
    def test_dmesg_d(self):
        """`dmesg -d' produces valid output"""
        self.command.invoke_uncaught("-d")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    @skip_with_symbol('log_first_seq')
    def test_dmesg_d(self):
        """`dmesg -d' raises CommandError with unstructured log"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("-d")

    def test_dmesg_m(self):
        """`dmesg -m ' produces valid output"""
        self.command.invoke_uncaught("-m")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_dmesg_tm(self):
        """`dmesg -t -m' produces valid output"""
        self.command.invoke_uncaught("-t -m")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    @skip_without_symbol('log_first_seq')
    def test_dmesg_td(self):
        """`dmesg -t -d' produces valid output"""
        self.command.invoke_uncaught("-t -d")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    @skip_without_symbol('log_first_seq')
    def test_dmesg_dm(self):
        """`dmesg -m -d' produces valid output"""
        self.command.invoke_uncaught("-m -d")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    @skip_without_symbol('log_first_seq')
    def test_dmesg_tdm(self):
        """`dmesg -t -d -m' produces valid output"""
        self.command.invoke_uncaught("-t -d -m")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    @skip_with_symbol('log_first_seq')
    def test_dmesg_td(self):
        """`dmesg -t -d' raises CommandError with unstructured log"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("-t -d")

    @skip_with_symbol('log_first_seq')
    def test_dmesg_dm(self):
        """`dmesg -m -d' raises CommandError with unstructured log"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("-m -d")

    @skip_with_symbol('log_first_seq')
    def test_dmesg_tdm(self):
        """`dmesg -t -d -m' raises CommandError with unstructured log"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("-t -d -m")

