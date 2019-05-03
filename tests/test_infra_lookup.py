# -*- coding: utf-8 -*- # vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb

from crash.exceptions import DelayedAttributeError
from crash.infra.callback import ObjfileEventCallback
from crash.infra.lookup import SymbolCallback, TypeCallback
from crash.infra.lookup import MinimalSymbolCallback
from crash.infra.lookup import DelayedType, DelayedSymbol, DelayedSymval
from crash.infra.lookup import DelayedMinimalSymbol, DelayedMinimalSymval

class TestTypeNameResolution(unittest.TestCase):
    def test_resolve_struct_normal(self):
        spec = 'struct test'

        (name, attrname, pointer) = TypeCallback.resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_struct_normal_pointer(self):
        spec = 'struct test *'

        (name, attrname, pointer) = TypeCallback.resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_p_type')
        self.assertTrue(pointer)

    def test_resolve_struct_leading_whitespace(self):
        spec = ' struct test'

        (name, attrname, pointer) = TypeCallback.resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_struct_trailing_whitespace(self):
        spec = 'struct test '

        (name, attrname, pointer) = TypeCallback.resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_struct_middle_whitespace(self):
        spec = 'struct    test'

        (name, attrname, pointer) = TypeCallback.resolve_type(spec)
        self.assertTrue(name == 'struct    test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_char(self):
        spec = 'char'

        (name, attrname, pointer) = TypeCallback.resolve_type(spec)
        self.assertTrue(name == 'char')
        self.assertTrue(attrname == 'char_type')
        self.assertFalse(pointer)

    def test_resolve_char_pointer(self):
        spec = 'char *'

        (name, attrname, pointer) = TypeCallback.resolve_type(spec)
        self.assertTrue(name == 'char')
        self.assertTrue(attrname == 'char_p_type')
        self.assertTrue(pointer)

class TestMinimalSymbolCallback(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")

    def tearDown(self):
        gdb.execute("file")

    def load_file(self):
        gdb.execute("file tests/test-util")

    def get_test_class(self):
        class test_class(object):
            def __init__(self):
                self.found = False
                cb = MinimalSymbolCallback('test_struct', self.callback)

            def callback(self, result):
                self.found = True
                self.result = result

        return test_class

    def test_minsymbol_no_symbol_found(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        gdb.execute("file tests/test-list")
        self.assertFalse(x.found)

    def test_minsymbol_found_immediately(self):
        test_class = self.get_test_class()
        self.load_file()
        x = test_class()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.result, gdb.MinSymbol))

    def test_minsymbol_found_after_load(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        self.load_file()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.result, gdb.MinSymbol))

    def test_minsymbol_not_found_in_early_load_then_found_after_load(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        gdb.execute("file tests/test-list")
        self.assertFalse(x.found)
        self.load_file()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.result, gdb.MinSymbol))

class TestSymbolCallback(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")

    def load_file(self):
        gdb.execute("file tests/test-util")

    def get_test_class(self):
        class test_class(object):
            def __init__(self):
                self.found = False
                cb = SymbolCallback('test_struct', self.callback)

            def callback(self, result):
                self.found = True
                self.result = result

        return test_class

    def test_symbol_no_symbol_found(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        gdb.execute("file tests/test-list")
        self.assertFalse(x.found)

    def test_symbol_found_immediately(self):
        test_class = self.get_test_class()
        self.load_file()
        x = test_class()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.result, gdb.Symbol))

    def test_symbol_found_after_load(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        self.load_file()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.result, gdb.Symbol))

    def test_symbol_not_found_in_early_load_then_found_after_load(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        gdb.execute("file tests/test-list")
        self.assertFalse(x.found)
        self.load_file()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.result, gdb.Symbol))

class TestTypeCallback(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")

    def load_file(self):
        gdb.execute("file tests/test-util")

    def get_test_class(self):
        class test_class(object):
            def __init__(self):
                self.found = False
                cb = TypeCallback('struct test', self.callback)

            def callback(self, result):
                self.found = True
                self.gdbtype = result

        return test_class

    def test_type_no_type_found(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        gdb.execute("file tests/test-list")
        self.assertFalse(x.found)

    def test_type_found_immediately(self):
        test_class = self.get_test_class()
        self.load_file()
        x = test_class()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.gdbtype, gdb.Type))

    def test_type_found_after_load(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        self.load_file()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.gdbtype, gdb.Type))

    def test_type_not_found_in_early_load_then_found_after_load(self):
        test_class = self.get_test_class()
        x = test_class()
        self.assertFalse(x.found)
        gdb.execute("file tests/test-list")
        self.assertFalse(x.found)
        self.load_file()
        self.assertTrue(x.found)
        self.assertTrue(isinstance(x.gdbtype, gdb.Type))
