# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys


from crash.commands.cgroup import CgroupCommand
from crash.commands import CommandLineError

class TestCommandsCgroup(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        self.redirected = io.StringIO()
        sys.stdout = self.redirected
        self.command = CgroupCommand("cgroup")
        # cgrp_dfl_root is available since v3.15-rc1
        cgroup_root = gdb.lookup_symbol('cgrp_dfl_root', None)[0].value()
        self.cgrp_dfl_root = cgroup_root['cgrp']

    def tearDown(self):
        sys.stdout = self.stdout

    def output(self):
        return self.redirected.getvalue()

    def output_lines(self):
        output = self.output()
        return len(output.split("\n")) - 1

    def test_proc_cgroup(self):
        """`cgroup` lists controllers"""
        self.command.invoke_uncaught(f"")
        # header + listing (at least one controller)
        self.assertTrue(self.output_lines() > 1)

    def test_cgroup_tasks(self):
        """`cgroup -g` lists cgroup tasks"""
        addr = int(self.cgrp_dfl_root.address)
        self.command.invoke_uncaught(f"-g {addr:x}")
        # header + listing (at least one task)
        self.assertTrue(self.output_lines() > 1)


