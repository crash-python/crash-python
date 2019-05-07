# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb


import crash.types.node as numa_node

class TestNumaNode(unittest.TestCase):
    def test_for_each_node(self):
        count = 0
        for node in numa_node.for_each_node():
            self.assertTrue(type(node) is numa_node.Node)
            count += 1
        self.assertTrue(count > 0)

    def test_for_each_online_node(self):
        count = 0
        for node in numa_node.for_each_online_node():
            self.assertTrue(type(node) is numa_node.Node)
            count += 1
        self.assertTrue(count > 0)

    def test_for_each_nid(self):
        count = 0
        for nid in numa_node.for_each_nid():
            self.assertTrue(type(nid) is int)
            count += 1
        self.assertTrue(count > 0)

    def test_for_each_online_nid(self):
        count = 0
        for nid in numa_node.for_each_online_nid():
            self.assertTrue(type(nid) is int)
            count += 1
        self.assertTrue(count > 0)

    def test_numa_node_id(self):
        nid = numa_node.numa_node_id(0)
        self.assertTrue(type(nid) is int)

