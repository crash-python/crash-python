# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb
import os.path
from kdump.target import Target

class TestUtil(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")
        self.do_real_tests = os.path.exists("tests/vmcore")

    def tearDown(self):
        try:
            x = gdb.current_target()
            del x
        except:
            pass
        gdb.execute('target exec')

    def test_bad_file(self):
        x = Target()
        with self.assertRaises(gdb.error):
            gdb.execute('target kdumpfile /does/not/exist')
        x.unregister()

    def test_real_open_with_no_kernel(self):
        if self.do_real_tests:
            x = Target()
            with self.assertRaises(gdb.error):
                gdb.execute('target kdumpfile tests/vmcore')
            x.unregister()

