# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb

from crash.infra import CrashBaseClass, export

# The delayed init tests check for presence of an attribute in the instance
# dict (or class dict for class attributes) since hasattr() will call
# __getattr__, causing delayed initialization to occur.

class TestInfra(unittest.TestCase):
    def test_exporter_baseline(self):
        class test_class(CrashBaseClass):
            inited = False
            def __init__(self):
                self.retval = 1020
                setattr(self.__class__, 'inited', True)
            @export
            def test_func(self):
                return self.retval

        x = test_class()
        self.assertTrue(x.inited)

        self.assertTrue(test_class.inited)
        self.assertTrue(test_func() == 1020)
        self.assertTrue(test_class.inited)

    def test_export_normal(self):
        class test_class(CrashBaseClass):
            @export
            def test_func(self):
                return 104

        self.assertTrue(test_func() == 104)

    def test_static_export(self):
        class test_class(CrashBaseClass):
            @staticmethod
            @export
            def test_func():
                return 1050

        self.assertTrue(test_func() == 1050)

    def test_export_static(self):
        class test_class(CrashBaseClass):
            @export
            @staticmethod
            def test_func():
                return 105

        self.assertTrue(test_func() == 105)

    def test_export_class(self):
        class test_class(CrashBaseClass):
            @classmethod
            @export
            def test_func(self):
                return 106

        self.assertTrue(test_func() == 106)

    def test_export_multiple_exports_one_instance(self):
        class test_class(CrashBaseClass):
            instances = 0
            def __init__(self):
                setattr(self.__class__, 'instances', self.instances + 1)

            @export
            def test_func(self):
                return 1060
            @export
            def test_func2(self):
                return 1061

        self.assertTrue(test_class.instances == 0)
        self.assertTrue(test_func() == 1060)
        self.assertTrue(test_class.instances == 1)
        self.assertTrue(test_func() == 1060)
        self.assertTrue(test_class.instances == 1)
        self.assertTrue(test_func2() == 1061)
        self.assertTrue(test_class.instances == 1)
        self.assertTrue(test_func2() == 1061)
        self.assertTrue(test_class.instances == 1)
