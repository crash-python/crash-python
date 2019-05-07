# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

import crash.types.bitmap as bitmaps

class TestBitmap(unittest.TestCase):
    def test_for_each_set_bit(self):
        sym = gdb.lookup_symbol('cpu_online_mask', None)[0]
        if sym is None:
            sym = gdb.lookup_symbol('__cpu_online_mask', None)[0]

        self.assertTrue(sym is not None)

        bitmap = sym.value()['bits']

        count = 0
        for bit in bitmaps.for_each_set_bit(bitmap):
            self.assertTrue(type(bit) is int)
            count += 1

        self.assertTrue(count > 0)

    def test_find_first_set_bit(self):
        sym = gdb.lookup_symbol('cpu_online_mask', None)[0]
        if sym is None:
            sym = gdb.lookup_symbol('__cpu_online_mask', None)[0]

        self.assertTrue(sym is not None)

        bitmap = sym.value()['bits']

        count = 0
        bit = bitmaps.find_first_set_bit(bitmap)
        self.assertTrue(type(bit) is int)

    def test_find_next_set_bit(self):
        sym = gdb.lookup_symbol('cpu_online_mask', None)[0]
        if sym is None:
            sym = gdb.lookup_symbol('__cpu_online_mask', None)[0]

        self.assertTrue(sym is not None)

        bitmap = sym.value()['bits']

        count = 0
        bit = bitmaps.find_next_set_bit(bitmap, 1)
        self.assertTrue(type(bit) is int)

    def test_find_first_zero_bit(self):
        sym = gdb.lookup_symbol('cpu_online_mask', None)[0]
        if sym is None:
            sym = gdb.lookup_symbol('__cpu_online_mask', None)[0]

        self.assertTrue(sym is not None)

        bitmap = sym.value()['bits']

        count = 0
        bit = bitmaps.find_first_zero_bit(bitmap)
        self.assertTrue(type(bit) is int)

    def test_find_next_zero_bit(self):
        sym = gdb.lookup_symbol('cpu_online_mask', None)[0]
        if sym is None:
            sym = gdb.lookup_symbol('__cpu_online_mask', None)[0]

        self.assertTrue(sym is not None)

        bitmap = sym.value()['bits']

        count = 0
        bit = bitmaps.find_next_zero_bit(bitmap, 10)
        self.assertTrue(type(bit) is int)

