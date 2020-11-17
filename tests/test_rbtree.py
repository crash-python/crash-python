# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb

from crash.types.rbtree import rbtree_postorder_for_each, rbtree_postorder_for_each_entry

def get_symbol(name):
    return gdb.lookup_symbol(name, None)[0].value()

class TestRbtree(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-rbtree", to_string=True)
        try:
            print()
            print("--- Unsuppressable gdb output ---", end='')

            gdb.execute("run", to_string=False)
            self.number_node_type = gdb.lookup_type("struct number_node")
        except gdb.error as e:
            # If we don't tear it down, the rest of the tests in
            # other files will fail due to it using the wrong core file
            self.tearDown()
            raise(e)

    def tearDown(self):
        try:
            gdb.execute("detach", to_string=True)
            gdb.execute("file")
        except gdb.error:
            print()
            pass
        print("--- End gdb output ---")

    def test_none_root(self):
        count = 0
        with self.assertRaises(TypeError):
            for node in rbtree_postorder_for_each(None):
                count += 1

    def test_invalid_value(self):
        count = 0
        gdbtype = gdb.lookup_type('unsigned int')
        with self.assertRaises(TypeError):
            for node in rbtree_postorder_for_each(gdbtype):
                count += 1

    def test_invalid_value_pointer(self):
        count = 0
        gdbtype = gdb.lookup_type('unsigned int').pointer()
        with self.assertRaises(TypeError):
            for node in rbtree_postorder_for_each(gdbtype):
                count += 1

    def test_nonroot_value(self):
        count = 0
        nn = get_symbol('naked_node')
        with self.assertRaises(TypeError):
            for node in rbtree_postorder_for_each(nn):
                count += 1

    def test_empty_tree(self):
        count = 0
        root = get_symbol('empty_tree_root')
        for node in rbtree_postorder_for_each(root):
            count += 1

        self.assertEqual(count, 0)

    def test_singular_tree(self):
        count = 0
        root = get_symbol('singular_tree_root')
        for node in rbtree_postorder_for_each(root):
            count += 1

        self.assertEqual(count, 1)

    def test_linear_binary_tree(self):
        vals = []
        root = get_symbol('linear_binary_tree_root')
        for node in rbtree_postorder_for_each_entry(root, self.number_node_type, 'rb'):
            vals.append(int(node['v']))

        self.assertEqual(vals, [2, 1, 0])

    def test_full_binary_tree(self):
        vals = []
        root = get_symbol('full_binary_tree_root')
        for node in rbtree_postorder_for_each_entry(root, self.number_node_type, 'rb'):
            vals.append(int(node['v']))

        self.assertEqual(vals, [3, 4, 1, 5, 6, 2, 0])

