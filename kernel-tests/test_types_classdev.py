# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

import crash.types.classdev as classdevs

class TestClassdev(unittest.TestCase):
    def setUp(self):
        self.device_type = gdb.lookup_type('struct device')

    def test_classdev_iteration(self):
        count = 0
        block_class = gdb.lookup_symbol('block_class', None)[0].value()
        for dev in classdevs.for_each_class_device(block_class):
            self.assertTrue(type(dev) is gdb.Value)
            self.assertTrue(dev.type == self.device_type)
            count += 1

        self.assertTrue(count > 0)

