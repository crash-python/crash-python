# -*- coding: utf-8 -*- # vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb

from crash.infra import CrashBaseClass
from crash.exceptions import DelayedAttributeError
from crash.infra.callback import ObjfileEventCallback
from crash.infra.lookup import SymbolCallback, TypeCallback
from crash.infra.lookup import MinimalSymbolCallback
from crash.infra.lookup import DelayedLookups, ClassProperty
from crash.infra.lookup import DelayedType, DelayedSymbol, DelayedSymval
from crash.infra.lookup import DelayedMinimalSymbol, DelayedMinimalSymval

class TestDelayedLookupSetup(unittest.TestCase):
    def test_resolve_struct_normal(self):
        spec = 'struct test'

        (name, attrname, pointer) = DelayedLookups._resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_struct_normal_pointer(self):
        spec = 'struct test *'

        (name, attrname, pointer) = DelayedLookups._resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_p_type')
        self.assertTrue(pointer)

    def test_resolve_struct_leading_whitespace(self):
        spec = ' struct test'

        (name, attrname, pointer) = DelayedLookups._resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_struct_trailing_whitespace(self):
        spec = 'struct test '

        (name, attrname, pointer) = DelayedLookups._resolve_type(spec)
        self.assertTrue(name == 'struct test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_struct_middle_whitespace(self):
        spec = 'struct    test'

        (name, attrname, pointer) = DelayedLookups._resolve_type(spec)
        self.assertTrue(name == 'struct    test')
        self.assertTrue(attrname == 'test_type')
        self.assertFalse(pointer)

    def test_resolve_char(self):
        spec = 'char'

        (name, attrname, pointer) = DelayedLookups._resolve_type(spec)
        self.assertTrue(name == 'char')
        self.assertTrue(attrname == 'char_type')
        self.assertFalse(pointer)

    def test_resolve_char_pointer(self):
        spec = 'char *'

        (name, attrname, pointer) = DelayedLookups._resolve_type(spec)
        self.assertTrue(name == 'char')
        self.assertTrue(attrname == 'char_p_type')
        self.assertTrue(pointer)

    def test_name_collision_attrs(self):
        class test_data(object):
            def __init__(self):
                self.name = 'foo'
            def get(self):
                pass
            def set(self, value):
                pass
        d = {'__delayed_lookups__' : {}}
        attr = test_data()
        DelayedLookups.add_lookup('TestClass', d, 'foo', attr)
        with self.assertRaises(NameError):
            DelayedLookups.add_lookup('TestClass', d, 'foo', attr)

    def test_name_collision_reserved(self):
        d = {'__delayed_lookups__' : {}}
        with self.assertRaises(NameError):
            DelayedLookups.setup_delayed_lookups_for_class('TestClass', d)

    def test_type_setup(self):
        d = {'__types__' : [ 'void *', 'struct test' ] }
        DelayedLookups.setup_delayed_lookups_for_class('TestClass', d)
        self.assertFalse('__types__' in d)
        self.assertTrue('void_p_type' in d)
        self.assertTrue(isinstance(d['void_p_type'], ClassProperty))
        self.assertTrue('void_p_type' in d['__delayed_lookups__'])
        self.assertTrue(isinstance(d['__delayed_lookups__']['void_p_type'],
                                   DelayedType))
        self.assertTrue('test_type' in d)
        self.assertTrue(isinstance(d['test_type'], ClassProperty))
        self.assertTrue('test_type' in d['__delayed_lookups__'])
        self.assertTrue(isinstance(d['__delayed_lookups__']['test_type'],
                                   DelayedType))
    def test_symbol_setup(self):
        d = {'__symbols__' : [ 'main' ]}
        DelayedLookups.setup_delayed_lookups_for_class('TestClass', d)
        self.assertFalse('__symbols__' in d)
        self.assertTrue('main' in d)
        self.assertTrue(isinstance(d['main'], ClassProperty))
        self.assertTrue('main' in d['__delayed_lookups__'])
        self.assertTrue(isinstance(d['__delayed_lookups__']['main'],
                                   DelayedSymbol))

    def test_symval_setup(self):
        d = {'__symvals__' : [ 'main' ]}
        DelayedLookups.setup_delayed_lookups_for_class('TestClass', d)
        self.assertFalse('__symvals__' in d)
        self.assertTrue('main' in d)
        self.assertTrue(isinstance(d['main'], ClassProperty))
        self.assertTrue('main' in d['__delayed_lookups__'])
        self.assertTrue(isinstance(d['__delayed_lookups__']['main'],
                                   DelayedSymval))

    def test_symval_setup_bad(self):
        d = {'__symvals__' : 'main' }
        with self.assertRaises(TypeError):
            DelayedLookups.setup_delayed_lookups_for_class('TestClass', d)

    def test_minsymbol_setup(self):
        d = {'__minsymbols__' : [ 'main' ]}
        DelayedLookups.setup_delayed_lookups_for_class('TestClass', d)
        self.assertFalse('__minsymbols__' in d)
        self.assertTrue('main' in d)
        self.assertTrue(isinstance(d['main'], ClassProperty))
        self.assertTrue('main' in d['__delayed_lookups__'])
        self.assertTrue(isinstance(d['__delayed_lookups__']['main'],
                                   DelayedMinimalSymbol))
    def test_minsymval_setup(self):
        d = {'__minsymvals__' : [ 'main' ]}
        DelayedLookups.setup_delayed_lookups_for_class('TestClass', d)
        self.assertFalse('__minsymvals__' in d)
        self.assertTrue('main' in d)
        self.assertTrue(isinstance(d['main'], ClassProperty))
        self.assertTrue('main' in d['__delayed_lookups__'])
        self.assertTrue(isinstance(d['__delayed_lookups__']['main'],
                                   DelayedMinimalSymval))

    def get_callback_class(self):
        class TestClass(DelayedLookups):
            @classmethod
            def main_callback(self, value):
                self.main_value = value

            @classmethod
            def voidp_callback(self, value):
                self.voidp_value = value

        return TestClass

    def test_type_callback_setup(self):
        TestClass = self.get_callback_class()
        d = {'__type_callbacks__' : [ ('void *', 'voidp_callback') ],
             '__delayed_lookups__' : {} }
        DelayedLookups.setup_named_callbacks(TestClass, d)
        self.assertFalse('__type_callbacks__' in d)

    def test_type_callback_setup_bad(self):
        TestClass = self.get_callback_class()
        d = {'__type_callbacks__' : [ 'void *', 'voidp_callback' ],
             '__delayed_lookups__' : {} }
        with self.assertRaises(ValueError):
            DelayedLookups.setup_named_callbacks(TestClass, d)

    def test_symbol_callback_setup(self):
        TestClass = self.get_callback_class()
        d = {'__symbol_callbacks__' : [ ('main', 'main_callback') ],
             '__delayed_lookups__' : {} }
        DelayedLookups.setup_named_callbacks(TestClass, d)
        self.assertFalse('__symbol_callbacks__' in d)

    def test_symbol_callback_setup_bad(self):
        TestClass = self.get_callback_class()
        d = {'__symbol_callbacks__' : [ 'main', 'main_callback' ],
             '__delayed_lookups__' : {} }
        with self.assertRaises(ValueError):
            DelayedLookups.setup_named_callbacks(TestClass, d)

    def test_minsymbol_callback_setup(self):
        TestClass = self.get_callback_class()
        d = {'__minsymbol_callbacks__' : [ ('main', 'main_callback') ],
             '__delayed_lookups__' : {} }
        DelayedLookups.setup_named_callbacks(TestClass, d)
        self.assertFalse('__minsymbol_callbacks__' in d)

    def test_minsymbol_callback_setup_bad(self):
        TestClass = self.get_callback_class()
        d = {'__minsymbol_callbacks__' : [ 'main', 'main_callback' ],
             '__delayed_lookups__' : {} }
        with self.assertRaises(ValueError):
            DelayedLookups.setup_named_callbacks(TestClass, d)

class TestMinimalSymbolCallback(unittest.TestCase):
    def setUp(self):
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

class TestDelayedLookup(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")

    def load_file(self):
        gdb.execute("file tests/test-util")

    def msymbol_test(self):
        class Test(CrashBaseClass):
            __minsymbols__ = [ 'test_struct' ]
        return Test

    def test_bad_msymbol_name(self):
        test = self.msymbol_test()
        x = test
        with self.assertRaises(AttributeError):
            y = x.bad_symbol_name

    def test_msymbol_unavailable_at_start(self):
        test = self.msymbol_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct

    def test_msymbol_available_on_load(self):
        test = self.msymbol_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct
        self.load_file()
        self.assertTrue(isinstance(x.test_struct, gdb.MinSymbol))

    def test_msymbol_available_at_start(self):
        test = self.msymbol_test()
        self.load_file()

        x = test()
        self.assertTrue(isinstance(x.test_struct, gdb.MinSymbol))

    def symbol_test(self):
        class Test(CrashBaseClass):
            __symbols__ = [ 'test_struct' ]
        return Test

    def test_bad_symbol_name(self):
        test = self.symbol_test()
        x = test
        with self.assertRaises(AttributeError):
            y = x.bad_symbol_name

    def test_symbol_unavailable_at_start(self):
        test = self.symbol_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct

    def test_symbol_available_on_load(self):
        test = self.symbol_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct
        self.load_file()
        self.assertTrue(isinstance(x.test_struct, gdb.Symbol))

    def test_symbol_available_at_start(self):
        test = self.symbol_test()
        self.load_file()

        x = test()
        self.assertTrue(isinstance(x.test_struct, gdb.Symbol))

    def symval_test(self):
        class Test(CrashBaseClass):
            __symvals__ = [ 'test_struct' ]
        return Test

    def test_bad_symval_name(self):
        test = self.symval_test()
        x = test
        with self.assertRaises(AttributeError):
            y = x.bad_symval_name

    def test_symval_unavailable_at_start(self):
        test = self.symval_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct

    def test_symval_available_on_load(self):
        test = self.symval_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct
        self.load_file()
        self.assertTrue(isinstance(x.test_struct, gdb.Value))

    def test_symval_available_at_start(self):
        test = self.symval_test()
        self.load_file()

        x = test()
        self.assertTrue(isinstance(x.test_struct, gdb.Value))

    def type_test(self):
        class Test(CrashBaseClass):
            __types__ = [ 'struct test' ]
        return Test

    def test_bad_type_name(self):
        test = self.type_test()
        x = test
        with self.assertRaises(AttributeError):
            y = x.bad_type_name

    def test_type_unavailable_at_start(self):
        test = self.type_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_type

    def test_type_available_on_load(self):
        test = self.type_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_type
        self.load_file()
        y = x.test_type
        self.assertTrue(isinstance(y, gdb.Type))

    def test_type_available_at_start(self):
        test = self.type_test()
        self.load_file()

        x = test()
        y = x.test_type
        self.assertTrue(isinstance(y, gdb.Type))

    def ptype_test(self):
        class Test(CrashBaseClass):
            __types__ = [ 'struct test *' ]
        return Test

    def test_bad_ptype_name(self):
        test = self.ptype_test()
        x = test
        with self.assertRaises(AttributeError):
            y = x.bad_ptype_name

    def test_p_type_unavailable_at_start(self):
        test = self.ptype_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_p_type

    def test_p_type_available_on_load(self):
        test = self.ptype_test()
        x = test()
        with self.assertRaises(DelayedAttributeError):
            y = x.test_p_type
        self.load_file()
        y = x.test_p_type
        self.assertTrue(isinstance(y, gdb.Type))

    def test_p_type_available_at_start(self):
        test = self.ptype_test()
        self.load_file()

        x = test()
        y = x.test_p_type
        self.assertTrue(isinstance(y, gdb.Type))

    def type_callback_test(self):
        class Test(CrashBaseClass):
            __type_callbacks__ = [
                ('unsigned long', 'check_ulong')
                ]
            ulong_valid = False
            @classmethod
            def check_ulong(cls, gdbtype):
                cls.ulong_valid = True

        return Test

    def test_type_callback_nofile(self):
        test = self.type_callback_test()
        x = test()
        self.assertFalse(test.ulong_valid)
        with self.assertRaises(AttributeError):
            y = x.unsigned_long_type

    def test_type_callback(self):
        test = self.type_callback_test()
        x = test()
        self.load_file()
        self.assertTrue(test.ulong_valid)
        with self.assertRaises(AttributeError):
            y = x.unsigned_long_type

    def type_callback_test_multi(self):
        class Test(CrashBaseClass):
            __types__ = [ 'unsigned long' ]
            __type_callbacks__ = [
                ('unsigned long', 'check_ulong')
                ]
            ulong_valid = False
            @classmethod
            def check_ulong(cls, gdbtype):
                cls.ulong_valid = True

        return Test

    def test_type_callback_nofile_multi(self):
        test = self.type_callback_test_multi()
        x = test()
        self.assertFalse(test.ulong_valid)
        with self.assertRaises(DelayedAttributeError):
            y = x.unsigned_long_type

    def test_type_callback_multi(self):
        test = self.type_callback_test_multi()
        x = test()
        self.load_file()
        self.assertTrue(test.ulong_valid)
        y = x.unsigned_long_type
        self.assertTrue(isinstance(y, gdb.Type))
        self.assertTrue(y.sizeof > 4)
