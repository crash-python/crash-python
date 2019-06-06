# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from decorators import bad_command_line, unimplemented

from crash.commands.vtop import VTOPCommand
from crash.commands import CommandError, CommandLineError
from crash.exceptions import DelayedAttributeError

class TestCommandsVTOP(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        self.redirected = io.StringIO()
        sys.stdout = self.redirected
        self.command = VTOPCommand()
        self.addr = int(gdb.lookup_symbol('modules', None)[0].value().address)

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return self.redirected.getvalue()

    def output_lines(self):
        output = self.output()
        return len(output.split("\n")) - 1

    @bad_command_line
    def test_vtop_empty(self):
        """Test `vtop`"""
        self.command.invoke_uncaught("")

    @bad_command_line
    def test_vtop_symname(self):
        """Test `vtop <symname>`"""
        self.command.invoke_uncaught("modules")
 
    def test_vtop_addr(self):
        """`Test vtop <addr>`"""
        self.command.invoke_uncaught(f"{self.addr:#x}")
        self.assertTrue(self.output_lines() > 0)

    def test_vtop_addr_k(self):
        """`Test vtop -k <addr>`"""
        self.command.invoke_uncaught(f"-k {self.addr:#x}")
        self.assertTrue(self.output_lines() > 0)

    def test_vtop_addr_u(self):
        """`Test vtop -u <addr>`"""
        self.command.invoke_uncaught(f"-u {self.addr:#x}")
        self.assertTrue(self.output_lines() > 0)

    @bad_command_line
    def test_vtop_addr_uk(self):
        """`Test vtop -k -u <addr>`"""
        self.command.invoke_uncaught(f"-k -u {self.addr:#x}")
        
    @unimplemented
    def test_vtop_addr_c(self):
        """Test `vtop -c <addr>`"""
        self.command.invoke_uncaught(f"-c {self.addr:#x}")
