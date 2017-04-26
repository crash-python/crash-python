# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest
import gdb

from crash.util import safe_get_symbol_value
from crash.infra.callback import ObjfileEventCallback

class TestCallback(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")

    def load_file(self):
        gdb.execute("file tests/test-util")

    def test_registering(self):
        class test_class(ObjfileEventCallback):
            def __init__(self):
                self.called = False
                self.checked = False
                super(test_class, self).__init__()

            def check_ready(self):
                self.checked = True
                return safe_get_symbol_value('main')

            def callback(self, result):
                self.called = True
                self.result = result

        x = test_class()
        self.assertFalse(x.called)
        self.assertFalse(x.completed)
        self.assertFalse(x.checked)
        self.load_file()
        self.assertTrue(x.checked)
        self.assertTrue(x.called)
        self.assertTrue(x.completed)
        self.assertTrue(isinstance(x.result, gdb.Value))
