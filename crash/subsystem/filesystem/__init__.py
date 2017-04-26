# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from crash.util import container_of
from crash.infra import CrashBaseClass, export
from crash.types.list import list_for_each_entry
from crash.subsystem.storage import block_device_name
from crash.subsystem.storage import Storage as block

class FileSystem(CrashBaseClass):
    __types__ = [ 'struct dio *',
                  'struct buffer_head *' ]
    __symbol_callbacks__ = [
                    ('dio_bio_end', 'register_dio_bio_end'),
                    ('dio_bio_end_aio', 'register_dio_bio_end'),
                    ('mpage_end_io', 'register_mpage_end_io') ]

    buffer_head_decoders = {}

    @classmethod
    def register_dio_bio(cls, symval):
        block.register_bio_decoder(cls.dio_bio_end, cls.decode_dio_bio)

    @classmethod
    def register_dio_bio_end(cls, sym):
        block.register_bio_decoder(sym, cls.decode_dio_bio)

    @classmethod
    def register_mpage_end_io(cls, sym):
        block.register_bio_decoder(sym, cls.decode_mpage)

    @export
    @staticmethod
    def super_fstype(sb):
        return sb['s_type']['name'].string()

    @export
    @classmethod
    def register_buffer_head_decoder(cls, sym, decoder):
        cls.buffer_head_decoders[sym] = decoder

    @classmethod
    def decode_dio_bio(cls, bio):
        dio = bio['bi_private'].cast(cls.dio_p_type)
        fstype = cls.super_fstype(dio['inode']['i_sb'])
        dev = block_device_name(dio['inode']['i_sb']['s_bdev'])
        offset = dio['block_in_file'] << dio['blkbits']

        chain = {
            'description' : "{:x} bio: Direct I/O for {} inode {} on {}".format(
                            long(bio), fstype, dio['inode']['i_ino'], dev),
            'bio' : bio,
            'dio' : dio,
            'fstype' : fstype,
            'inode' : dio['inode'],
            'offset' : offset,
            'devname' : dev,
        }
        return chain

    @classmethod
    def decode_mpage(cls, bio):
        inode = bio['bi_io_vec'][0]['bv_page']['mapping']['host']
        fstype = cls.super_fstype(inode['i_sb'])
        chain = {
            'description' :
                "{:x} bio: Multipage I/O: inode {}, type {}, dev {}".format(
                        long(bio), inode['i_ino'], fstype,
                        block_device_name(bio['bi_bdev'])),
            'bio' : bio,
            'fstype' : fstype,
            'inode' : inode,
        }
        return chain

    @classmethod
    def decode_bio_buffer_head(cls, bio):
        bh = bio['bi_private'].cast(cls.buffer_head_p_type)
        chain = {
            'description' :
                "{:x} bio: Bio representation of buffer head".format(long(bio)),
            'bio' : bio,
            'next' : bh,
            'decoder' : cls.decode_buffer_head,
        }

        return chain

    @classmethod
    def decode_buffer_head(cls, bh):
        endio = bh['b_end_io']
        try:
            return cls.buffer_head_decoders[endio](bh)
        except KeyError:
            pass
        desc = "{:x} buffer_head: for dev {}, block {}, size {} (undecoded)".format(
                    long(bh), block_device_name(bh['b_bdev']),
                    bh['b_blocknr'], bh['b_size'])
        chain = {
            'description' : desc,
            'bh' : bh,
        }
        return chain

    @classmethod
    def decode_end_buffer_write_sync(cls, bh):
        desc = ("{:x} buffer_head: for dev {}, block {}, size {} (unassociated)"
                .format(block_device_name(bh['b_bdev']),
                        bh['b_blocknr'], bh['b_size']))
        chain = {
            'description' : desc,
            'bh' : bh,
        }
        return chain

inst = FileSystem()
