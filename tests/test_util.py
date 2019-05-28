# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

from crash.exceptions import MissingTypeError, MissingSymbolError
from crash.util import offsetof, container_of, resolve_type
from crash.util import get_symbol_value, safe_get_symbol_value
from crash.exceptions import ArgumentTypeError
from crash.exceptions import NotStructOrUnionError
from crash.util import InvalidComponentError

def getsym(sym):
    return gdb.lookup_symbol(sym, None)[0].value()

class TestUtil(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-util")
        self.ulong = gdb.lookup_type('unsigned long')
        self.ulongsize = self.ulong.sizeof
        self.test_struct = gdb.lookup_type("struct test")

    def tearDown(self):
        gdb.execute("file")

    def test_invalid_python_type(self):
        with self.assertRaises(ArgumentTypeError):
            offset = offsetof(self, 'dontcare')

    def test_type_by_string_name(self):
        offset = offsetof('struct test', 'test_member')
        self.assertTrue(offset == 0)

    def test_type_by_invalid_name(self):
        with self.assertRaises(ArgumentTypeError):
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
        with self.assertRaises(NotStructOrUnionError):
            offset = offsetof('unsigned long', 'test_member')

    def test_ulong_by_type(self):
        t = gdb.lookup_type("unsigned long")
        with self.assertRaises(NotStructOrUnionError):
            offset = offsetof(t, 'test_member')

    def test_ulong_by_type_pointer(self):
        t = gdb.lookup_type("unsigned long").pointer()
        with self.assertRaises(NotStructOrUnionError):
            offset = offsetof(t, 'test_member')

    def test_ulong_by_symbol(self):
        t = gdb.lookup_global_symbol('global_ulong_symbol')
        with self.assertRaises(NotStructOrUnionError):
            offset = offsetof(t, 'test_member')

    def test_ulong_by_value(self):
        t = gdb.lookup_global_symbol('global_ulong_symbol').value()
        with self.assertRaises(NotStructOrUnionError):
            offset = offsetof(t, 'test_member')

    def test_void_pointer_by_symbol(self):
        t = gdb.lookup_global_symbol('global_void_pointer_symbol')
        with self.assertRaises(NotStructOrUnionError):
            offset = offsetof(t, 'test_member')

    def test_void_pointer_by_value(self):
        t = gdb.lookup_global_symbol('global_void_pointer_symbol').value()
        with self.assertRaises(NotStructOrUnionError):
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


    def test_resolve_type(self):
        t = gdb.lookup_type('unsigned long')
        resolved_type = resolve_type(t)
        self.assertTrue(t == resolved_type)

    def test_resolve_type_by_value(self):
        v = gdb.Value(10)
        resolved_type = resolve_type(v)
        self.assertTrue(v.type == resolved_type)

    def test_resolve_type_by_str_good(self):
        t = gdb.lookup_type('unsigned long')
        resolved_type = resolve_type('unsigned long')
        self.assertTrue(t == resolved_type)

    def test_resolve_type_by_str_bad(self):
        with self.assertRaises(MissingTypeError):
            resolved_type = resolve_type('unsigned long bad type')

    def test_resolve_type_by_sym(self):
        sym = gdb.lookup_symbol("test_struct", None)[0]
        resolved_type = resolve_type(sym)
        self.assertTrue(sym.value().type == resolved_type)

    def test_resolve_type_None(self):
        with self.assertRaises(TypeError):
            resolved_type = resolve_type(None)

    def test_container_of_sym(self):
        sym = gdb.lookup_symbol("test_struct", None)[0]
        with self.assertRaises(TypeError):
            print(container_of(sym, None, None))

    def test_get_symbol_value_good(self):
        sym = get_symbol_value("test_struct")
        self.assertTrue(isinstance(sym, gdb.Value))

    def test_get_symbol_value_good(self):
        with self.assertRaises(MissingSymbolError):
            sym = get_symbol_value("test_struct_bad")

    def test_safe_get_symbol_value_good(self):
        sym = safe_get_symbol_value("test_struct")
        self.assertTrue(isinstance(sym, gdb.Value))

    def test_safe_get_symbol_value_bad(self):
        sym = safe_get_symbol_value("test_struct_bad")
        self.assertTrue(sym is None)

    def test_container_of_long_container(self):
        sym = getsym('long_container')
        container = getsym('test_struct')
        addr = container_of(sym, self.test_struct, 'test_member')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_struct_long_container1(self):
        sym = getsym('anon_struct_long_container1')
        container = getsym('test_struct')
        addr = container_of(sym, self.test_struct, 'anon_struct_member1')
        self.assertTrue(sym.address != container.address)
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_struct_long_container2(self):
        sym = getsym('anon_struct_long_container2')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct, 'anon_struct_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_struct_embedded_container(self):
        sym = getsym('anon_struct_embedded_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_struct_embedded_struct')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_struct_embedded_member1_container(self):
        sym = getsym('anon_struct_embedded_member1_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_struct_embedded_struct.embedded_member1')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_struct_embedded_member2_container(self):
        sym = getsym('anon_struct_embedded_member2_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_struct_embedded_struct.embedded_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_struct_embedded_list_container(self):
        sym = getsym('anon_struct_embedded_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_struct_embedded_struct.embedded_list')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_union_long_container1(self):
        sym = getsym('anon_union_long_container1')
        container = getsym('test_struct')
        addr = container_of(sym, self.test_struct, 'anon_union_member1')
        self.assertTrue(sym.address != container.address)
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_union_long_container2(self):
        sym = getsym('anon_union_long_container2')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct, 'anon_union_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_union_embedded_container(self):
        sym = getsym('anon_union_embedded_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_union_embedded_struct')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_union_embedded_member1_container(self):
        sym = getsym('anon_union_embedded_member1_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_union_embedded_struct.embedded_member1')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_union_embedded_member2_container(self):
        sym = getsym('anon_union_embedded_member2_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_union_embedded_struct.embedded_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_anon_union_embedded_list_container(self):
        sym = getsym('anon_union_embedded_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'anon_union_embedded_struct.embedded_list')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_struct_long_container1(self):
        sym = getsym('named_struct_long_container1')
        container = getsym('test_struct')
        addr = container_of(sym, self.test_struct,
                            'named_struct.named_struct_member1')
        self.assertTrue(sym.address != container.address)
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_struct_long_container2(self):
        sym = getsym('named_struct_long_container2')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_struct.named_struct_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_struct_embedded_container(self):
        sym = getsym('named_struct_embedded_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_struct.named_struct_embedded_struct')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_struct_embedded_member1_container(self):
        sym = getsym('named_struct_embedded_member1_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_struct.named_struct_embedded_struct.embedded_member1')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_struct_embedded_member2_container(self):
        sym = getsym('named_struct_embedded_member2_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_struct.named_struct_embedded_struct.embedded_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_struct_embedded_list_container(self):
        sym = getsym('named_struct_embedded_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_struct.named_struct_embedded_struct.embedded_list')
        self.assertTrue(addr.address == container.address)


    def test_container_of_named_union_long_container1(self):
        sym = getsym('named_union_long_container1')
        container = getsym('test_struct')
        addr = container_of(sym, self.test_struct,
                            'named_union.named_union_member1')
        self.assertTrue(sym.address != container.address)
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_union_long_container2(self):
        sym = getsym('named_union_long_container2')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_union.named_union_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_union_embedded_container(self):
        sym = getsym('named_union_embedded_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_union.named_union_embedded_struct')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_union_embedded_member1_container(self):
        sym = getsym('named_union_embedded_member1_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_union.named_union_embedded_struct.embedded_member1')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_union_embedded_member2_container(self):
        sym = getsym('named_union_embedded_member2_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_union.named_union_embedded_struct.embedded_member2')
        self.assertTrue(addr.address == container.address)

    def test_container_of_named_union_embedded_list_container(self):
        sym = getsym('named_union_embedded_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'named_union.named_union_embedded_struct.embedded_list')
        self.assertTrue(addr.address == container.address)

    def test_container_of_embedded_struct_container(self):
        sym = getsym('embedded_struct_container')
        container = getsym('test_struct')
        addr = container_of(sym, self.test_struct, 'embedded_struct_member')
        self.assertTrue(sym.address != container.address)
        self.assertTrue(addr.address == container.address)

    def test_container_of_embedded_struct_member1(self):
        sym = getsym('embedded_struct_member1_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'embedded_struct_member.embedded_member1')
        self.assertTrue(addr.address == container.address)

    def test_container_of_embedded_struct_member2(self):
        sym = getsym('embedded_struct_member2_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'embedded_struct_member.embedded_member2')

    def test_container_of_embedded_struct_list(self):
        sym = getsym('embedded_struct_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        addr = container_of(sym, self.test_struct,
                            'embedded_struct_member.embedded_list')

    def test_container_of_bad_name(self):
        sym = getsym('embedded_struct_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        with self.assertRaises(InvalidComponentError):
            addr = container_of(sym, self.test_struct, 'bad_name')

    def test_container_of_bad_intermediate_name2(self):
        sym = getsym('embedded_struct_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        with self.assertRaises(InvalidComponentError):
            addr = container_of(sym, self.test_struct,
                                'embedded_member.good')

    def test_container_of_bad_type(self):
        sym = getsym('embedded_struct_list_container')
        container = getsym('test_struct')
        self.assertTrue(sym.address != container.address)
        with self.assertRaises(NotStructOrUnionError):
            addr = container_of(sym, self.ulong, 'test_member')
