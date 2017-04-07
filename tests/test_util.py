# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb

from crash.types.util import offsetof
from crash.types.util import InvalidComponentError
from crash.types.util import InvalidArgumentError
from crash.types.util import InvalidArgumentTypeError

class TestUtil(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-util.o")
        self.ulongsize = gdb.lookup_type('unsigned long').sizeof
        self.test_struct = gdb.lookup_type("struct test")

    def test_invalid_python_type(self):
        with self.assertRaises(InvalidArgumentError):
            offset = offsetof(self, 'dontcare')

    def test_type_by_string_name(self):
        offset = offsetof('struct test', 'test_member')
        self.assertTrue(offset == 0)

    def test_type_by_invalid_name(self):
        with self.assertRaises(InvalidArgumentError):
            offset = offsetof('struct invalid_struct', 'test_member')

    def test_invalid_member(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'invalid_member')

    def test_struct_by_symbol(self):
        val = gdb.lookup_global_symbol("global_struct_symbol")
        offset = offsetof(val, 'test_member')
        self.assertTrue(offset == 0)

    def test_struct_by_value(self):
        val = gdb.lookup_global_symbol("global_struct_symbol").value()
        offset = offsetof(val, 'test_member')
        self.assertTrue(offset == 0)

    def test_ulong_by_name(self):
        with self.assertRaises(InvalidArgumentTypeError):
            offset = offsetof('unsigned long', 'test_member')

    def test_ulong_by_type(self):
        t = gdb.lookup_type("unsigned long")
        with self.assertRaises(InvalidArgumentTypeError):
            offset = offsetof(t, 'test_member')

    def test_ulong_by_type_pointer(self):
        t = gdb.lookup_type("unsigned long").pointer()
        with self.assertRaises(InvalidArgumentTypeError):
            offset = offsetof(t, 'test_member')

    def test_ulong_by_symbol(self):
        t = gdb.lookup_global_symbol('global_ulong_symbol')
        with self.assertRaises(InvalidArgumentTypeError):
            offset = offsetof(t, 'test_member')

    def test_ulong_by_value(self):
        t = gdb.lookup_global_symbol('global_ulong_symbol').value()
        with self.assertRaises(InvalidArgumentTypeError):
            offset = offsetof(t, 'test_member')

    def test_void_pointer_by_symbol(self):
        t = gdb.lookup_global_symbol('global_void_pointer_symbol')
        with self.assertRaises(InvalidArgumentTypeError):
            offset = offsetof(t, 'test_member')

    def test_void_pointer_by_value(self):
        t = gdb.lookup_global_symbol('global_void_pointer_symbol').value()
        with self.assertRaises(InvalidArgumentTypeError):
            offset = offsetof(t, 'test_member')

    def test_union_by_symbol(self):
        t = gdb.lookup_global_symbol('global_union_symbol')
        offset = offsetof(t, 'member1')
        self.assertTrue(offset == 0)

    def test_union_by_value(self):
        t = gdb.lookup_global_symbol('global_union_symbol').value()
        offset = offsetof(t, 'member1')
        self.assertTrue(offset == 0)

    def test_struct(self):
        offset = offsetof(self.test_struct, 'test_member')
        self.assertTrue(offset == 0)

    def test_struct_pointer(self):
        offset = offsetof(self.test_struct.pointer(), 'test_member')
        self.assertTrue(offset == 0)

    def test_anon_struct_member1(self):
        offset = offsetof(self.test_struct, 'anon_struct_member1')
        self.assertTrue(offset == self.ulongsize)

    def test_anon_struct_member2(self):
        offset = offsetof(self.test_struct, 'anon_struct_member2')
        self.assertTrue(offset == 2*self.ulongsize)

    def test_anon_struct_pointer_member1(self):
        offset = offsetof(self.test_struct.pointer(), 'anon_struct_member1')
        self.assertTrue(offset == self.ulongsize)

    def test_anon_struct_pointer_member2(self):
        offset = offsetof(self.test_struct.pointer(), 'anon_struct_member2')
        self.assertTrue(offset == 2*self.ulongsize)

    def test_anon_struct_embedded_struct(self):
        offset = offsetof(self.test_struct, 'anon_struct_embedded_struct')
        self.assertTrue(offset == 3*self.ulongsize)

    def test_anon_struct_embedded_struct_pointer(self):
        offset = offsetof(self.test_struct.pointer(),
                         'anon_struct_embedded_struct')
        self.assertTrue(offset == 3*self.ulongsize)

    def test_anon_struct_embedded_struct_member1(self):
        offset = offsetof(self.test_struct,
                         'anon_struct_embedded_struct.embedded_member1')
        self.assertTrue(offset == 3*self.ulongsize)

    def test_anon_struct_embedded_struct_member1_pointer(self):
        offset = offsetof(self.test_struct.pointer(),
                         'anon_struct_embedded_struct.embedded_member1')
        self.assertTrue(offset == 3*self.ulongsize)

    def test_anon_struct_embedded_struct_member2(self):
        offset = offsetof(self.test_struct,
                         'anon_struct_embedded_struct.embedded_member2')
        self.assertTrue(offset == 4*self.ulongsize)

    def test_anon_struct_embedded_struct_member2_pointer(self):
        offset = offsetof(self.test_struct.pointer(),
                         'anon_struct_embedded_struct.embedded_member2')
        self.assertTrue(offset == 4*self.ulongsize)

    def test_anon_struct_embedded_struct_list(self):
        offset = offsetof(self.test_struct,
                         'anon_struct_embedded_struct.embedded_list')
        self.assertTrue(offset == 5*self.ulongsize)

    def test_anon_struct_embedded_struct_list_pointer(self):
        offset = offsetof(self.test_struct.pointer(),
                         'anon_struct_embedded_struct.embedded_list')
        self.assertTrue(offset == 5*self.ulongsize)

    def test_anon_struct_embedded_struct_list_next(self):
        offset = offsetof(self.test_struct,
                         'anon_struct_embedded_struct.embedded_list.next')
        self.assertTrue(offset == 5*self.ulongsize)

    def test_anon_struct_embedded_struct_list_next_pointer(self):
        offset = offsetof(self.test_struct.pointer(),
                         'anon_struct_embedded_struct.embedded_list.next')
        self.assertTrue(offset == 5*self.ulongsize)

    def test_anon_struct_embedded_struct_list_prev(self):
        offset = offsetof(self.test_struct,
                         'anon_struct_embedded_struct.embedded_list.prev')
        self.assertTrue(offset == 6*self.ulongsize)

    def test_anon_struct_embedded_struct_list_prev(self):
        offset = offsetof(self.test_struct.pointer(),
                         'anon_struct_embedded_struct.embedded_list.prev')
        self.assertTrue(offset == 6*self.ulongsize)

    def test_named_struct(self):
        offset = offsetof(self.test_struct, 'named_struct')
        self.assertTrue(offset == 7*self.ulongsize)

    def test_named_struct_member1(self):
        offset = offsetof(self.test_struct, 'named_struct.named_struct_member1')
        self.assertTrue(offset == 7*self.ulongsize)

    def test_named_struct_member2(self):
        offset = offsetof(self.test_struct, 'named_struct.named_struct_member2')
        self.assertTrue(offset == 8*self.ulongsize)

    def test_named_struct_pointer_member1(self):
        offset = offsetof(self.test_struct.pointer(), 'named_struct.named_struct_member1')
        self.assertTrue(offset == 7*self.ulongsize)

    def test_named_struct_pointer_member2(self):
        offset = offsetof(self.test_struct.pointer(), 'named_struct.named_struct_member2')
        self.assertTrue(offset == 8*self.ulongsize)

    def test_anon_union_member1(self):
        offset = offsetof(self.test_struct, 'anon_union_member1')
        self.assertTrue(offset == 13*self.ulongsize)

    def test_anon_union_member2(self):
        offset = offsetof(self.test_struct, 'anon_union_member2')
        self.assertTrue(offset == 13*self.ulongsize)

    def test_anon_union_pointer_member1(self):
        offset = offsetof(self.test_struct.pointer(), 'anon_union_member1')
        self.assertTrue(offset == 13*self.ulongsize)

    def test_anon_union_pointer_member2(self):
        offset = offsetof(self.test_struct.pointer(), 'anon_union_member2')
        self.assertTrue(offset == 13*self.ulongsize)

    def test_named_union_named_member1(self):
        offset = offsetof(self.test_struct, 'named_union.named_union_member1')
        self.assertTrue(offset == 17*self.ulongsize)

    def test_named_union_anon_member1(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'named_union_member1')

    def test_named_union_named_member2(self):
        offset = offsetof(self.test_struct, 'named_union.named_union_member2')
        self.assertTrue(offset == 17*self.ulongsize)

    def test_named_union_anon_member2(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'named_union_member1')

    def test_embedded_struct(self):
        offset = offsetof(self.test_struct, 'embedded_struct_member')
        self.assertTrue(offset == 21*self.ulongsize)

    def test_embedded_struct_member1(self):
        offset = offsetof(self.test_struct,
                          'embedded_struct_member.embedded_member1')
        self.assertTrue(offset == 21*self.ulongsize)

    def test_embedded_struct_member2(self):
        offset = offsetof(self.test_struct,
                          'embedded_struct_member.embedded_member2')
        self.assertTrue(offset == 22*self.ulongsize)

    def test_embedded_struct_anon_member1(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'embedded_member1')

    def test_embedded_struct_anon_member2(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'embedded_member2')

    def test_enum_lookup(self):
        offset = offsetof(self.test_struct, 'enum_member')
        self.assertTrue(offset == 26*self.ulongsize)

    def test_enum_invalid_lookup(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'enum_member.invalid')

    def test_multi_level_lookup_list_next(self):
        offset = offsetof(self.test_struct,
                          'embedded_struct_member.embedded_list.next')
        self.assertTrue(offset == 23*self.ulongsize)

    def test_multi_level_lookup_list_prev(self):
        offset = offsetof(self.test_struct,
                          'embedded_struct_member.embedded_list.prev')
        self.assertTrue(offset == 24*self.ulongsize)

    def test_multi_level_lookup_missing_first_component(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'missing.embedded_list.prev')

    def test_multi_level_lookup_missing_middle_component(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct,
                              'embedded_struct_member.invalid.prev')

    def test_multi_level_lookup_missing_last_component(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct,
                              'embedded_struct_member.embedded_list.invalid')

    def test_multi_level_lookup_invalid_first_component(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct, 'test_member.next_component')

    def test_multi_level_lookup_invalid_middle_component(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct,
                              'embedded_struct_member.embedded_member1.next_component')

    def test_multi_level_lookup_anon_struct_missing_component(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct,
                              'anon_struct_embedded_struct.invalid.next_component')

    def test_multi_level_lookup_anon_union_missing_component(self):
        with self.assertRaises(InvalidComponentError):
            offset = offsetof(self.test_struct,
                              'anon_union_embedded_struct.invalid.next_component')
