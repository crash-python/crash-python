# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb
import os.path
from crash.kdump.target import Target

class TestUtil(unittest.TestCase):
    def setUp(self):
        self.do_real_tests = os.path.exists("tests/vmcore")

    def test_bad_file(self):
        with self.assertRaises(TypeError):
            x = Target("/does/not/exist")

    def test_real_open_with_no_kernel(self):
        if self.do_real_tests:
            with self.assertRaises(RuntimeError):
                x = Target("tests/vmcore")
