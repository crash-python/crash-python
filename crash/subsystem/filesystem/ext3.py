# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gdb
import sys

if sys.version_info.major >= 3:
    long = int

from crash.infra import CrashBaseClass
from crash.util import get_symbol_value
from crash.subsystem.filesystem import register_buffer_head_decoder

class Ext3(CrashBaseClass):
    __symbol_callbacks__ = [
            ('journal_end_buffer_io_sync', '_register_journal_buffer_io_sync') ]

    @classmethod
    def _register_journal_buffer_io_sync(cls, sym):
        # ext3/ext4 and jbd/jbd2 share names but not implementations
        b = gdb.block_for_pc(long(sym.value().address))
        sym = get_symbol_value('journal_end_buffer_io_sync', b)

        register_buffer_head_decoder(sym, cls.decode_journal_buffer_io_sync)

    @classmethod
    def decode_journal_buffer_io_sync(cls, bh):
        """
        Decodes an ext3 journal buffer

        This method decodes a struct buffer_head with and end_io callback
        of journal_end_buffer_io_sync.

        Args:
            bh (gdb.Value<struct buffer_head>): The struct buffer_head to
                decode

        Returns:
            dict: Contains the following items:
                - description (str): Human-readable description of
                    the buffer head
                - bh (gdb.Value<struct buffer_head>): The buffer head being
                    decoded
                - fstype (str): The name of the file system type being decoded
                - devname (str): The name of the device the file system uses
                - offset (long): The offset, in bytes, of the block described
                - length (long): The length of the block described
        """

        fstype = "journal on ext3"
        devname = block_device_name(bh['b_bdev'])
        chain = {
            'bh' : bh,
            'description' : "{:x} buffer_head: {} journal block (jbd) on {}".format(long(bh), fstype, devname),
            'fstype' : fstype,
            'devname' : devname,
            'offset' : long(bh['b_blocknr']) * long(bh['b_size']),
            'length' : long(bh['b_size'])
        }

        return chain
