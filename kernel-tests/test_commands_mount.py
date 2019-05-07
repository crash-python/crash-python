# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

from crash.commands.mount import MountCommand

class TestCommandsMount(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        sys.stdout = io.StringIO()
        self.command = MountCommand("mount")

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return sys.stdout.getvalue()

    def test_mount(self):
        self.command.invoke("")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_mount_f(self):
        self.command.invoke("-f")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_mount_v(self):
        self.command.invoke("-v")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)

    def test_mount_d(self):
        self.command.invoke("-d")
        output = self.output()
        self.assertTrue(len(output.split("\n")) > 2)
