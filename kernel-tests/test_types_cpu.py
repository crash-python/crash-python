# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

import crash.types.cpu as cpus

class TestCPU(unittest.TestCase):
    def test_online_cpu_iteration(self):
        count = 0
        for cpu in cpus.for_each_online_cpu():
            self.assertTrue(type(cpu) is int)
            count += 1

        self.assertTrue(count > 0)

    def test_highest_online_cpu(self):
        cpu = cpus.highest_online_cpu_nr()
        self.assertTrue(type(cpu) is int)

    def test_possible_cpu_iteration(self):
        count = 0
        for cpu in cpus.for_each_possible_cpu():
            self.assertTrue(type(cpu) is int)
            count += 1

        self.assertTrue(count > 0)

    def test_highest_possible_cpu(self):
        cpu = cpus.highest_possible_cpu_nr()
        self.assertTrue(type(cpu) is int)
