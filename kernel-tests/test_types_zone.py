# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb


import crash.types.node as numa_node
import crash.types.zone as mmzone

class TestNumaNode(unittest.TestCase):
    def test_for_each_zone(self):
        count = 0
        for node in numa_node.for_each_node():
            for zone in node.for_each_zone():
                self.assertTrue(type(zone) is mmzone.Zone)
                count += 1

        self.assertTrue(count > 0)

    def test_for_each_populated_zone(self):
        count = 0
        for zone in mmzone.for_each_populated_zone():
            self.assertTrue(type(zone) is mmzone.Zone)
            count += 1

        self.assertTrue(count > 0)

