# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb

from crash.infra import delayed_init, exporter

class TestInfra(unittest.TestCase):
    def test_delayed_init_then_exporter(self):
        @exporter
        @delayed_init
        class test_class(object):
            def __init__(self):
                self.class_voidp = gdb.lookup_type("void").pointer()

        self.assertTrue(True)


    # This should be unnecessary but for now throwing an exception is
    # easier than fixing it properly.
    def test_exporter_then_delayed_init(self):
        with self.assertRaises(RuntimeError):
            @delayed_init
            @exporter
            class test_class(object):
                def __init__(self):
                    self.class_voidp = gdb.lookup_type("void").pointer()
