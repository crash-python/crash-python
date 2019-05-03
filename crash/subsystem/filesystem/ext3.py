# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.subsystem.storage.decoders import Decoder

class Ext3Decoder(Decoder):
    """
    Decodes an ext3 journal buffer

    This decodes a struct buffer_head with an end_io callback
    of journal_end_buffer_io_sync.

    Args:
        bh (gdb.Value<struct buffer_head>): The struct buffer_head to decode
    """

    __endio__ = 'journal_end_buffer_io_sync'
    description = "{:x} buffer_head: {} journal block (jbd) on {}"

    def __init__(self, bh):
        super().__init__()
        self.bh = bh

    def interpret(self):
        self.fstype = "journal on ext3"
        self.devname = block_device_name(self.bh['b_bdev'])
        self.offset = int(self.bh['b_blocknr']) * int(self.bh['b_size'])
        self.length = int(self.bh['b_size'])

    def __str__(self):
        return self.description(int(self.bh), fstype, devname)

Ext3Decoder.register()
