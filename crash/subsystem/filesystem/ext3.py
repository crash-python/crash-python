# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.subsystem.storage import block_device_name
from crash.subsystem.storage.decoders import Decoder

class Ext3Decoder(Decoder):
    """
    Decodes an ext3 journal buffer

    This decodes a ``struct buffer_head`` with a `b_end_io` callback
    of ``journal_end_buffer_io_sync``.

    Args:
        bh: The struct buffer_head to decode.  The value must be of
            type ``struct buffer_head``.

    Attributes:
        fstype (str): "journal on ext3"
        devname (str): The device name in string form
        offset (int): The starting offset of this buffer on the device
        length (int): The length of buffer on the the device
    """

    __endio__ = 'journal_end_buffer_io_sync'
    _description = "{:x} buffer_head: {} journal block (jbd) on {}"

    def __init__(self, bh: gdb.Value) -> None:
        super().__init__()
        self.bh = bh

    def interpret(self) -> None:
        """Interprets the ext3 buffer_head to populate its attributes"""
        # pylint: disable=attribute-defined-outside-init
        self.fstype = "journal on ext3"
        self.devname = block_device_name(self.bh['b_bdev'])
        self.offset = int(self.bh['b_blocknr']) * int(self.bh['b_size'])
        self.length = int(self.bh['b_size'])

    def __str__(self) -> str:
        return self._description.format(int(self.bh), self.fstype, self.devname)

Ext3Decoder.register()
