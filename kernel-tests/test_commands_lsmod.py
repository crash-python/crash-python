# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from crash.commands.lsmod import ModuleCommand

class TestCommandsLsmod(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = io.StringIO()

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return sys.stdout.getvalue()

    def test_lsmod(self):
        ModuleCommand().invoke("")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_lsmod_wildcard(self):
        ModuleCommand().invoke("*")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_lsmod_p(self):
        ModuleCommand().invoke("-p")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)
        print(output)

    def test_lsmod_p_0(self):
        ModuleCommand().invoke("-p 0")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)
