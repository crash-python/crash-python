# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb

from crash.types.list import list_for_each, list_for_each_entry
from crash.types.list import ListCycleError, CorruptListError

def get_symbol(name):
    return gdb.lookup_symbol(name, None)[0].value()

class TestList(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-list")
        self.list_head = gdb.lookup_type("struct list_head")

    def tearDown(self):
        gdb.execute("file")

    def test_none_list(self):
        count = 0
        with self.assertRaises(TypeError):
            for node in list_for_each(None):
                count += 1

    def test_invalid_value(self):
        count = 0
        gdbtype = gdb.lookup_type('unsigned int')
        with self.assertRaises(TypeError):
            for node in list_for_each(gdbtype):
                count += 1

    def test_invalid_value_pointer(self):
        count = 0
        gdbtype = gdb.lookup_type('unsigned int').pointer()
        with self.assertRaises(TypeError):
            for node in list_for_each(gdbtype):
                count += 1

    def test_bad_next_pointer_list(self):
        head = get_symbol("bad_next_ptr_list")
        count = 0

        with self.assertRaises(BufferError):
            for node in list_for_each(head):
                count += 1

#    Not a failure yet - we don't iterate the list backward
#    def test_bad_prev_pointer_list(self):
#        head = get_symbol("bad_prev_ptr_list")
#        count = 0
#
#        with self.assertRaises(BufferError):
#            for node in list_for_each(head):
#                count += 1

    def test_normal_list(self):
        normal_list = get_symbol("normal_head")
        short_list = get_symbol("short_list")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof
        count = 0
        for node in list_for_each(normal_list):
            count += 1

        self.assertTrue(count == expected_count)

    def test_cycle_list(self):
        normal_list = get_symbol("cycle_head")
        short_list = get_symbol("short_list_with_cycle")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof
        count = 0
        with self.assertRaises(ListCycleError):
            for node in list_for_each(normal_list, exact_cycles=True):
                count += 1

    def test_corrupt_list(self):
        normal_list = get_symbol("bad_list_head")
        short_list = get_symbol("short_list_with_bad_prev")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof
        count = 0
        with self.assertRaises(CorruptListError):
            for node in list_for_each(normal_list, exact_cycles=True,
                                      print_broken_links=False):
                count += 1

    def test_normal_container_list_with_string(self):
        normal_list = get_symbol("good_container_list")
        short_list = get_symbol("good_containers")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof

        count = 0
        for node in list_for_each_entry(normal_list, 'struct container',
                                        'list'):
            count += 1

        self.assertTrue(count == expected_count)

    def test_normal_container_list_with_type(self):
        normal_list = get_symbol("good_container_list")
        short_list = get_symbol("good_containers")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof
        struct_container = gdb.lookup_type('struct container')

        count = 0
        for node in list_for_each_entry(normal_list, struct_container, 'list'):
            count += 1

    def test_cycle_container_list_with_string(self):
        cycle_list = get_symbol("cycle_container_list")
        short_list = get_symbol("cycle_containers")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof

        count = 0
        with self.assertRaises(ListCycleError):
            for node in list_for_each_entry(cycle_list, 'struct container',
                                            'list', exact_cycles=True,
                                            print_broken_links=False):
                count += 1

    def test_cycle_container_list_with_type(self):
        cycle_list = get_symbol("cycle_container_list")
        short_list = get_symbol("cycle_containers")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof
        struct_container = gdb.lookup_type('struct container')

        count = 0
        with self.assertRaises(ListCycleError):
            for node in list_for_each_entry(cycle_list, struct_container,
                                            'list', exact_cycles=True,
                                            print_broken_links=False):
                count += 1

    def test_bad_container_list_with_string(self):
        bad_list = get_symbol("bad_container_list")
        short_list = get_symbol("bad_containers")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof

        count = 0
        with self.assertRaises(CorruptListError):
            for node in list_for_each_entry(bad_list, 'struct container',
                                            'list', print_broken_links=False):
                count += 1

    def test_bad_container_list_with_type(self):
        bad_list = get_symbol("bad_container_list")
        short_list = get_symbol("bad_containers")
        expected_count = short_list.type.sizeof // short_list[0].type.sizeof
        struct_container = gdb.lookup_type('struct container')

        count = 0
        with self.assertRaises(CorruptListError):
            for node in list_for_each_entry(bad_list, struct_container,
                                            'list', print_broken_links=False):
                count += 1
