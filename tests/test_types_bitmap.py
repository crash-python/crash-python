# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import sys

import crash.types.bitmap as bm

import gdb

class TestBitmap(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-percpu")
        ulong = gdb.lookup_type('unsigned long')
        ulong_array = ulong.array(0)

    # 10101010010100101010100010101001000101001000100010100101001001001010010
        val = 0x552954548A445292

        self.bitmap = gdb.Value(val.to_bytes(8, sys.byteorder), ulong_array)

    def test_test_bit(self):
        self.assertFalse(bm.test_bit(self.bitmap, 0))
        self.assertTrue(bm.test_bit(self.bitmap, 1))
        self.assertFalse(bm.test_bit(self.bitmap, 2))
        self.assertFalse(bm.test_bit(self.bitmap, 3))
        self.assertTrue(bm.test_bit(self.bitmap, 4))
        self.assertFalse(bm.test_bit(self.bitmap, 5))
        self.assertFalse(bm.test_bit(self.bitmap, 6))
        self.assertTrue(bm.test_bit(self.bitmap, 7))
        self.assertFalse(bm.test_bit(self.bitmap, 8))
        self.assertTrue(bm.test_bit(self.bitmap, 9))
        self.assertFalse(bm.test_bit(self.bitmap, 10))
        self.assertFalse(bm.test_bit(self.bitmap, 11))
        self.assertTrue(bm.test_bit(self.bitmap, 12))
        self.assertFalse(bm.test_bit(self.bitmap, 13))
        self.assertTrue(bm.test_bit(self.bitmap, 14))
        self.assertFalse(bm.test_bit(self.bitmap, 15))
        self.assertFalse(bm.test_bit(self.bitmap, 16))
        self.assertFalse(bm.test_bit(self.bitmap, 17))
        self.assertTrue(bm.test_bit(self.bitmap, 18))
        self.assertFalse(bm.test_bit(self.bitmap, 19))
        self.assertFalse(bm.test_bit(self.bitmap, 20))
        self.assertFalse(bm.test_bit(self.bitmap, 21))
        self.assertTrue(bm.test_bit(self.bitmap, 22))
        self.assertFalse(bm.test_bit(self.bitmap, 23))
        self.assertFalse(bm.test_bit(self.bitmap, 24))
        self.assertTrue(bm.test_bit(self.bitmap, 25))
        self.assertFalse(bm.test_bit(self.bitmap, 26))
        self.assertTrue(bm.test_bit(self.bitmap, 27))
        self.assertFalse(bm.test_bit(self.bitmap, 28))
        self.assertFalse(bm.test_bit(self.bitmap, 29))
        self.assertFalse(bm.test_bit(self.bitmap, 30))
        self.assertTrue(bm.test_bit(self.bitmap, 31))
        self.assertFalse(bm.test_bit(self.bitmap, 32))
        self.assertFalse(bm.test_bit(self.bitmap, 33))
        self.assertTrue(bm.test_bit(self.bitmap, 34))
        self.assertFalse(bm.test_bit(self.bitmap, 35))
        self.assertTrue(bm.test_bit(self.bitmap, 36))
        self.assertFalse(bm.test_bit(self.bitmap, 37))
        self.assertTrue(bm.test_bit(self.bitmap, 38))
        self.assertFalse(bm.test_bit(self.bitmap, 39))
        self.assertFalse(bm.test_bit(self.bitmap, 40))
        self.assertFalse(bm.test_bit(self.bitmap, 41))
        self.assertTrue(bm.test_bit(self.bitmap, 42))
        self.assertFalse(bm.test_bit(self.bitmap, 43))
        self.assertTrue(bm.test_bit(self.bitmap, 44))
        self.assertFalse(bm.test_bit(self.bitmap, 45))
        self.assertTrue(bm.test_bit(self.bitmap, 46))
        self.assertFalse(bm.test_bit(self.bitmap, 47))
        self.assertTrue(bm.test_bit(self.bitmap, 48))
        self.assertFalse(bm.test_bit(self.bitmap, 49))
        self.assertFalse(bm.test_bit(self.bitmap, 50))
        self.assertTrue(bm.test_bit(self.bitmap, 51))
        self.assertFalse(bm.test_bit(self.bitmap, 52))
        self.assertTrue(bm.test_bit(self.bitmap, 53))
        self.assertFalse(bm.test_bit(self.bitmap, 54))
        self.assertFalse(bm.test_bit(self.bitmap, 55))
        self.assertTrue(bm.test_bit(self.bitmap, 56))
        self.assertFalse(bm.test_bit(self.bitmap, 57))
        self.assertTrue(bm.test_bit(self.bitmap, 58))
        self.assertFalse(bm.test_bit(self.bitmap, 59))
        self.assertTrue(bm.test_bit(self.bitmap, 60))
        self.assertFalse(bm.test_bit(self.bitmap, 61))
        self.assertTrue(bm.test_bit(self.bitmap, 62))
        self.assertFalse(bm.test_bit(self.bitmap, 63))

    def test_for_each_set_bit(self):
        count = 0
        for bit in bm.for_each_set_bit(self.bitmap):
            count += 1

        self.assertTrue(count == 24)

    def test_find_first_set_bit(self):
        bit = bm.find_first_set_bit(self.bitmap)
        self.assertTrue(bit == 2)

    def test_find_first_zero_bit(self):
        bit = bm.find_first_zero_bit(self.bitmap)
        self.assertTrue(bit == 1)

    def test_find_next_set_bit(self):
        bit = bm.find_next_set_bit(self.bitmap, 27)
        self.assertTrue(bit == 28)

    def test_find_next_zero_bit(self):
        bit = bm.find_next_zero_bit(self.bitmap,  51)
        self.assertTrue(bit == 53)

    def test_find_last_set_bit(self):
        bit = bm.find_last_set_bit(self.bitmap)
        self.assertTrue(bit == 63)
