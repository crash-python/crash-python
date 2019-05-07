# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from decorators import skip_without_symbol
from decorators import skip_with_symbol

from crash.commands.kmem import KmemCommand
from crash.commands import CommandLineError, CommandError

class TestCommandsKmem(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = io.StringIO()
        self.command = KmemCommand("kmem")

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return sys.stdout.getvalue()

    def test_kmem_empty(self):
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("")

    def test_kmem_invalid(self):
        """`kmem' returns error"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("invalid")

    @unittest.skip("takes a huge amount of time on a real core")
    def test_kmem_s(self):
        """`kmem -s' produces valid output"""
        self.command.invoke_uncaught("-s")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_kmem_s_inode_cache(self):
        """`kmem -s inode_cache' produces valid output"""
        self.command.invoke_uncaught("-s inode_cache")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_kmem_s_unknown_cache(self):
        """`kmem -s unknown_cache' raises CommandError"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("-s unknown_cache")

    def test_kmem_sz(self):
        """`kmem -s -z' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-s -z")

    def test_kmem_sz_valid_cache(self):
        """`kmem -s -z' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-s inode_cache -z")

    def test_kmem_sz_invalid_cache(self):
        """`kmem -s unknown_cache -z' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-s unknown_cache -z")

    def test_kmem_sv(self):
        """`kmem -s -V' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-s -V")

    def test_kmem_sv_valid_cache(self):
        """`kmem -s inode_cache -V' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-s inode_cache -V")

    def test_kmem_sv_invalid_cache(self):
        """`kmem -s unknown_cache -V' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-s unknown_cache -V")

    def test_kmem_z(self):
        """`kmem -z' produces valid output"""
        self.command.invoke_uncaught("-z")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_kmem_z_invalid(self):
        """`kmem -z invalid' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-z invalid")

    @skip_without_symbol('vm_stat')
    def test_kmem_v(self):
        """`kmem -V' produces valid output"""
        self.command.invoke_uncaught("-V")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 0)

    @skip_with_symbol('vm_stat')
    def test_kmem_v_unimplemented(self):
        """`kmem -V' raises CommandError due to missing symbol"""
        with self.assertRaises(CommandError):
            self.command.invoke_uncaught("-V")

    def test_kmem_v_invalid(self):
        """`kmem -V invalid' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-V invalid")

    def test_kmem_vz(self):
        """`kmem -V -z' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-V -z")

    def test_kmem_svz(self):
        """`kmem -V -z -s' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-V -z -s")

    def test_kmem_svz_valid_cache(self):
        """`kmem -V -z -s inode_cache' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-V -z -s inode_cache")

    def test_kmem_svz_invalid_cache(self):
        """`kmem -V -z -s unknown_cache' raises CommandLineError"""
        with self.assertRaises(CommandLineError):
            self.command.invoke_uncaught("-V -z -s unknown_cache")
