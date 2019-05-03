# -*- coding: utf-8 -*- # vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb

from crash.exceptions import DelayedAttributeError

from crash.util.symbols import MinimalSymbols, Symbols, Symvals, Types
from crash.util.symbols import TypeCallbacks, SymbolCallbacks
from crash.util.symbols import MinimalSymbolCallbacks

class TestDelayedContainers(unittest.TestCase):
    def setUp(self):
        gdb.execute("file")

    def load_file(self):
        gdb.execute("file tests/test-util")

    def msymbol_test(self):
        class Test(object):
            msymbols = MinimalSymbols([ 'test_struct' ])
        return Test

    def test_bad_msymbol_name(self):
        test = self.msymbol_test()
        x = test.msymbols
        with self.assertRaises(AttributeError):
            y = x.bad_symbol_name

    def test_msymbol_unavailable_at_start(self):
        test = self.msymbol_test()
        x = test().msymbols
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct

    def test_msymbol_available_on_load(self):
        test = self.msymbol_test()
        x = test().msymbols
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct
        self.load_file()
        self.assertTrue(isinstance(x.test_struct, gdb.MinSymbol))

    def test_msymbol_available_at_start(self):
        test = self.msymbol_test()
        x = test().msymbols
        self.load_file()

        self.assertTrue(isinstance(x.test_struct, gdb.MinSymbol))

    def symbol_test(self):
        class Test(object):
            symbols = Symbols([ 'test_struct' ])
        return Test

    def test_bad_symbol_name(self):
        test = self.symbol_test()
        x = test.symbols
        with self.assertRaises(AttributeError):
            y = x.bad_symbol_name

    def test_symbol_unavailable_at_start(self):
        test = self.symbol_test()
        x = test().symbols
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct

    def test_symbol_available_on_load(self):
        test = self.symbol_test()
        x = test().symbols
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct
        self.load_file()
        self.assertTrue(isinstance(x.test_struct, gdb.Symbol))

    def test_symbol_available_at_start(self):
        test = self.symbol_test()
        self.load_file()

        x = test().symbols
        self.assertTrue(isinstance(x.test_struct, gdb.Symbol))

    def symval_test(self):
        class Test(object):
            symvals = Symvals( [ 'test_struct' ] )
        return Test

    def test_bad_symval_name(self):
        test = self.symval_test()
        x = test.symvals
        with self.assertRaises(AttributeError):
            y = x.bad_symval_name

    def test_symval_unavailable_at_start(self):
        test = self.symval_test()
        x = test().symvals
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct

    def test_symval_available_on_load(self):
        test = self.symval_test()
        x = test().symvals
        with self.assertRaises(DelayedAttributeError):
            y = x.test_struct
        self.load_file()
        self.assertTrue(isinstance(x.test_struct, gdb.Value))

    def test_symval_available_at_start(self):
        test = self.symval_test()
        self.load_file()

        x = test().symvals
        self.assertTrue(isinstance(x.test_struct, gdb.Value))

    def type_test(self):
        class Test(object):
            types = Types( [ 'struct test' ] )
        return Test

    def test_bad_type_name(self):
        test = self.type_test()
        x = test.types
        with self.assertRaises(AttributeError):
            y = x.bad_type_name

    def test_type_unavailable_at_start(self):
        test = self.type_test()
        x = test().types
        with self.assertRaises(DelayedAttributeError):
            y = x.test_type

    def test_type_available_on_load(self):
        test = self.type_test()
        x = test().types
        with self.assertRaises(DelayedAttributeError):
            y = x.test_type
        self.load_file()
        y = x.test_type
        self.assertTrue(isinstance(y, gdb.Type))

    def test_type_available_at_start(self):
        test = self.type_test()
        self.load_file()

        x = test().types
        y = x.test_type
        self.assertTrue(isinstance(y, gdb.Type))

    def ptype_test(self):
        class Test(object):
            types = Types( [ 'struct test *' ])
        return Test

    def test_bad_ptype_name(self):
        test = self.ptype_test()
        x = test.types
        with self.assertRaises(AttributeError):
            y = x.bad_ptype_name

    def test_p_type_unavailable_at_start(self):
        test = self.ptype_test()
        x = test().types
        with self.assertRaises(DelayedAttributeError):
            y = x.test_p_type

    def test_p_type_available_on_load(self):
        test = self.ptype_test()
        x = test().types
        with self.assertRaises(DelayedAttributeError):
            y = x.test_p_type
        self.load_file()
        y = x.test_p_type
        self.assertTrue(isinstance(y, gdb.Type))

    def test_p_type_available_at_start(self):
        test = self.ptype_test()
        self.load_file()

        x = test().types
        y = x.test_p_type
        self.assertTrue(isinstance(y, gdb.Type))

    def type_callback_test(self):
        class Test(object):
            class nested(object):
                ulong_valid = False

                @classmethod
                def check_ulong(cls, gdbtype):
                    cls.ulong_valid = True

            type_cbs = TypeCallbacks( [ ('unsigned long',
                                         nested.check_ulong) ] )
        return Test

    def test_type_callback_nofile(self):
        test = self.type_callback_test()
        x = test().nested
        self.assertFalse(x.ulong_valid)
        with self.assertRaises(AttributeError):
            y = x.unsigned_long_type

    def test_type_callback(self):
        test = self.type_callback_test()
        x = test().nested
        self.load_file()
        self.assertTrue(x.ulong_valid)
        with self.assertRaises(AttributeError):
            y = x.unsigned_long_type

    def type_callback_test_multi(self):
        class Test(object):
            class nested(object):
                types = Types( [ 'unsigned long' ] )

                ulong_valid = False

                @classmethod
                def check_ulong(cls, gdbtype):
                    cls.ulong_valid = True

            type_cbs = TypeCallbacks( [ ('unsigned long',
                                         nested.check_ulong) ] )

        return Test

    def test_type_callback_nofile_multi(self):
        test = self.type_callback_test_multi()
        x = test().nested
        self.assertFalse(x.ulong_valid)
        with self.assertRaises(DelayedAttributeError):
            y = x.types.unsigned_long_type

    def test_type_callback_multi(self):
        test = self.type_callback_test_multi()
        x = test().nested
        self.load_file()
        self.assertTrue(x.ulong_valid)
        y = x.types.unsigned_long_type
        self.assertTrue(isinstance(y, gdb.Type))
        self.assertTrue(y.sizeof > 4)
