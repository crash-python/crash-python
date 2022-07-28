# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
from unittest.mock import patch
import gdb

from crash.util import safe_get_symbol_value
from crash.infra.callback import ObjfileEventCallback

class TestCallback(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")

    def tearDown(self):
        gdb.execute("file")

    def load_file(self):
        gdb.execute("file tests/test-util")

    def get_test_class(self):
        class test_class(ObjfileEventCallback):
            def __init__(self, *args, **kwargs):
                self.called = False
                self.checked = False
                self.result = None
                super(test_class, self).__init__(*args, **kwargs)

                self.connect_callback()

            def check_ready(self):
                self.checked = True
                return safe_get_symbol_value('main')

            def callback(self, result):
                self.called = True
                self.result = result

        return test_class

    def test_registering(self):
        test_class = self.get_test_class()
        with patch.object(test_class, 'check_target', return_value=True):
            x = test_class()

        self.assertFalse(x.called)
        self.assertFalse(x.completed)
        self.assertFalse(x.checked)
        self.assertTrue(x.result is None)

        self.load_file()
        self.assertTrue(x.checked)
        self.assertTrue(x.called)
        self.assertTrue(x.completed)

        self.assertTrue(isinstance(x.result, gdb.Value))

    def test_early_callback_with_target_wait(self):
        test_class = self.get_test_class()

        x = test_class()

        self.assertFalse(x.called)
        self.assertFalse(x.completed)
        self.assertFalse(x.checked)
        self.assertTrue(x.result is None)

        self.load_file()
        self.assertFalse(x.called)
        self.assertFalse(x.completed)
        self.assertFalse(x.checked)
        self.assertTrue(x.result is None)

        x.target_ready()
        self.assertTrue(x.checked)
        self.assertTrue(x.called)
        self.assertTrue(x.completed)

        self.assertTrue(isinstance(x.result, gdb.Value))

    def test_early_callback_without_target_wait(self):
        test_class = self.get_test_class()

        x = test_class(False)

        self.assertFalse(x.called)
        self.assertFalse(x.completed)
        self.assertFalse(x.checked)
        self.assertTrue(x.result is None)

        self.load_file()
        self.assertTrue(x.called)
        self.assertTrue(x.completed)
        self.assertTrue(x.checked)
        self.assertTrue(isinstance(x.result, gdb.Value))

        x.target_ready()
        self.assertTrue(x.checked)
        self.assertTrue(x.called)
        self.assertTrue(x.completed)

        self.assertTrue(isinstance(x.result, gdb.Value))
