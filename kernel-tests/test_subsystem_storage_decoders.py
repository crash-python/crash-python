# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys

import crash.util as util
import crash.subsystem.storage.decoders as decoders

# We need live bios to be able to test this properly

class TestSubsystemStorageDecoders(unittest.TestCase):
    nullptr = 0x0
    poisonptr = 0xdead000000000100

    def setUp(self):
        self.bio_type = gdb.lookup_type('struct bio')
        self.buffer_head_type = gdb.lookup_type('struct buffer_head')

    def test_decode_null_bio(self):
        bio = util.get_typed_pointer(self.nullptr, self.bio_type)
        bio = bio.dereference()
        decoder = decoders.decode_bio(bio)
        self.assertTrue(type(decoder) is decoders.BadBioDecoder)

    def test_decode_poison_bio(self):
        bio = util.get_typed_pointer(self.poisonptr, self.bio_type)
        bio = bio.dereference()
        decoder = decoders.decode_bio(bio)
        self.assertTrue(type(decoder) is decoders.BadBioDecoder)

    def test_decode_null_bh(self):
        bh = util.get_typed_pointer(self.nullptr, self.buffer_head_type)
        bh = bh.dereference()
        decoder = decoders.decode_bh(bh)
        self.assertTrue(type(decoder) is decoders.BadBHDecoder)

    def test_decode_poison_bh(self):
        bh = util.get_typed_pointer(self.poisonptr, self.buffer_head_type)
        bh = bh.dereference()
        decoder = decoders.decode_bh(bh)
        self.assertTrue(type(decoder) is decoders.BadBHDecoder)
