# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

from crash.types.rbtree import rbtree_postorder_for_each, rbtree_postorder_for_each_entry

class TestRbtree(unittest.TestCase):
    def setUp(self):
        self.vmap_area_root = gdb.lookup_symbol('vmap_area_root')[0].value()
        self.vmap_area_type = gdb.lookup_type('struct vmap_area')
        self.rb_node_type = gdb.lookup_type('struct rb_node')

    def test_postorder_for_each(self):
        count = 0
        last = None
        for node in rbtree_postorder_for_each(self.vmap_area_root):
            count += 1
            last = node

        self.assertTrue(count > 0)
        self.assertTrue(last.type == self.rb_node_type)

    def test_postorder_for_each_entry(self):
        count = 0
        last = None
        for vmap_area in rbtree_postorder_for_each_entry(self.vmap_area_root,
                                                         self.vmap_area_type, 'rb_node'):
            count += 1
            last = vmap_area

        self.assertTrue(count > 0)
        self.assertTrue(last.type == self.vmap_area_type)
        self.assertTrue(int(last['va_start']) <= int(last['va_end']))
