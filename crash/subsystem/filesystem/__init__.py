# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable, Union

import gdb
from crash.util import container_of, get_typed_pointer, decode_flags
from crash.infra import CrashBaseClass, export
from crash.types.list import list_for_each_entry
from crash.subsystem.storage import block_device_name
from crash.subsystem.storage import Storage as block

AddressSpecifier = Union[int, str, gdb.Value]

MS_RDONLY       = 1
MS_NOSUID       = 2
MS_NODEV        = 4
MS_NOEXEC       = 8
MS_SYNCHRONOUS  = 16
MS_REMOUNT      = 32
MS_MANDLOCK     = 64
MS_DIRSYNC      = 128
MS_NOATIME      = 1024
MS_NODIRATIME   = 2048
MS_BIND         = 4096
MS_MOVE         = 8192
MS_REC          = 16384
MS_VERBOSE      = 32768
MS_SILENT       = 32768
MS_POSIXACL     = (1<<16)
MS_UNBINDABLE   = (1<<17)
MS_PRIVATE      = (1<<18)
MS_SLAVE        = (1<<19)
MS_SHARED       = (1<<20)
MS_RELATIME     = (1<<21)
MS_KERNMOUNT    = (1<<22)
MS_I_VERSION    = (1<<23)
MS_STRICTATIME  = (1<<24)
MS_LAZYTIME     = (1<<25)
MS_NOSEC        = (1<<28)
MS_BORN         = (1<<29)
MS_ACTIVE       = (1<<30)
MS_NOUSER       = (1<<31)

SB_FLAGS = {
    MS_RDONLY       : "MS_RDONLY",
    MS_NOSUID       : "MS_NOSUID",
    MS_NODEV        : "MS_NODEV",
    MS_NOEXEC       : "MS_NOEXEC",
    MS_SYNCHRONOUS  : "MS_SYNCHRONOUS",
    MS_REMOUNT      : "MS_REMOUNT",
    MS_MANDLOCK     : "MS_MANDLOCK",
    MS_DIRSYNC      : "MS_DIRSYNC",
    MS_NOATIME      : "MS_NOATIME",
    MS_NODIRATIME   : "MS_NODIRATIME",
    MS_BIND         : "MS_BIND",
    MS_MOVE         : "MS_MOVE",
    MS_REC          : "MS_REC",
    MS_SILENT       : "MS_SILENT",
    MS_POSIXACL     : "MS_POSIXACL",
    MS_UNBINDABLE   : "MS_UNBINDABLE",
    MS_PRIVATE      : "MS_PRIVATE",
    MS_SLAVE        : "MS_SLAVE",
    MS_SHARED       : "MS_SHARED",
    MS_RELATIME     : "MS_RELATIME",
    MS_KERNMOUNT    : "MS_KERNMOUNT",
    MS_I_VERSION    : "MS_I_VERSION",
    MS_STRICTATIME  : "MS_STRICTATIME",
    MS_LAZYTIME     : "MS_LAZYTIME",
    MS_NOSEC        : "MS_NOSEC",
    MS_BORN         : "MS_BORN",
    MS_ACTIVE       : "MS_ACTIVE",
    MS_NOUSER       : "MS_NOUSER",
}

class FileSystem(CrashBaseClass):
    __types__ = [ 'struct dio *',
                  'struct buffer_head *',
                  'struct super_block' ]
    __symvals__ = [ 'super_blocks' ]
    __symbol_callbacks__ = [
                    ('dio_bio_end_io', '_register_dio_bio_end'),
                    ('dio_bio_end_aio', '_register_dio_bio_end'),
                    ('mpage_end_io', '_register_mpage_end_io'),
                    ('end_bio_bh_io_sync', '_register_end_bio_bh_io_sync') ]

    buffer_head_decoders = {}

    @classmethod
    def _register_dio_bio(cls, symval):
        block.register_bio_decoder(cls.dio_bio_end, cls.decode_dio_bio)

    @classmethod
    def _register_dio_bio_end(cls, sym):
        block.register_bio_decoder(sym, cls.decode_dio_bio)

    @classmethod
    def _register_mpage_end_io(cls, sym):
        block.register_bio_decoder(sym, cls.decode_mpage)

    @classmethod
    def _register_end_bio_bh_io_sync(cls, sym):
        block.register_bio_decoder(sym, cls.decode_bio_buffer_head)

    @export
    @staticmethod
    def super_fstype(sb: gdb.Value) -> str:
        """
        Returns the file system type's name for a given superblock.

        Args:
            sb (gdb.Value<struct super_block>): The struct super_block for
                which to return the file system type's name

        Returns:
            str: The file system type's name
        """
        return sb['s_type']['name'].string()

    @export
    @staticmethod
    def super_flags(sb: gdb.Value) -> str:
        """
        Returns the flags associated with the given superblock.

        Args:
            sb (gdb.Value<struct super_block>): The struct super_block for
                which to return the flags.

        Returns:
            str: The flags field in human-readable form.

        """
        return decode_flags(sb['s_flags'], SB_FLAGS)

    @export
    @classmethod
    def register_buffer_head_decoder(cls, sym, decoder):
        """
        Registers a buffer_head decoder with the filesystem subsystem.

        A buffer_head decoder is a method thats acepts a buffer_head,
        potentially interprets the private members of the buffer_head,
        and returns a dictionary.  The only mandatory member of the
        dictionary is 'description' which contains a human-readable
        description of the purpose of this buffer_head.

        If the buffer_head is part of a stack, the 'next' item should contain
        the next object in the stack.  It does not necessarily need to be
        a buffer_head.  It does need to have a 'decoder' item declared
        that will accept the given object.  The decoder does not need to
        be registered unless it will be a top-level decoder.

        Other items can be added as-needed to allow informed callers
        to obtain direct informatiom.

        Args:
            sym (gdb.Value<void (*)(struct buffer_head *, int)>):
                The kernel function used as buffer_head->b_h_end_io callback
        """

        cls.buffer_head_decoders[sym] = decoder

    @classmethod
    def decode_dio_bio(cls, bio):
        """
        Decodes a bio used for direct i/o.

        This method decodes a bio generated by the direct-io component of
        the file system subsystem.  The bio can either have been submitted
        directly or asynchronously.

        Args:
            bio(gdb.Value<struct bio>): The struct bio to be decoded, generated
                by the direct i/o component

        Returns:
            dict: Contains the following items:
                - description (str): Human-readable description of the bio
                - bio (gdb.Value<struct bio>): The struct bio being decoded
                - dio (gdb.Value<struct dio>): The direct i/o component of
                    the bio
                - fstype (str): The name of the file system which submitted
                    this bio
                - inode (gdb.Value<struct inode>): The struct inode, if any,
                    that owns the file associated with this bio
                - offset (int): The offset within the file, in bytes
                - devname (str): The device name associated with this bio
        """
        dio = bio['bi_private'].cast(cls.dio_p_type)
        fstype = cls.super_fstype(dio['inode']['i_sb'])
        dev = block_device_name(dio['inode']['i_sb']['s_bdev'])
        offset = dio['block_in_file'] << dio['blkbits']

        chain = {
            'description' : "{:x} bio: Direct I/O for {} inode {}, sector {} on {}".format(
                            int(bio), fstype, dio['inode']['i_ino'],
                            bio['bi_sector'], dev),
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
        """
        Decodes a bio used for multipage i/o.

        This method decodes a bio generated by the mpage component of
        the file system subsystem.

        Args:
            bio(gdb.Value<struct bio>): The struct bio to be decoded, generated
                by the mpage component

        Returns:
            dict: Contains the following items:
                - description (str): Human-readable description of the bio
                - bio (gdb.Value<struct bio>): The struct bio being decoded
                - fstype (str): The name of the file system which submitted
                    this bio
                - inode (gdb.Value<struct inode>): The struct inode, if any,
                    that owns the file associated with this bio
        """
        inode = bio['bi_io_vec'][0]['bv_page']['mapping']['host']
        fstype = cls.super_fstype(inode['i_sb'])
        chain = {
            'description' :
                "{:x} bio: Multipage I/O: inode {}, type {}, dev {}".format(
                        int(bio), inode['i_ino'], fstype,
                        block_device_name(bio['bi_bdev'])),
            'bio' : bio,
            'fstype' : fstype,
            'inode' : inode,
        }
        return chain

    @classmethod
    def decode_bio_buffer_head(cls, bio):
        """
        Decodes a bio used to perform i/o for buffer_heads

        This method decodes a bio generated by buffer head submission.

        Args:
            bio(gdb.Value<struct bio>): The struct bio to be decoded, generated
                by buffer head submission

        Returns:
            dict: Contains the following items:
                - description (str): Human-readable description of the bio
                - bio (gdb.Value<struct bio>): The struct bio being decoded
                - next (gdb.Value<struct buffer_head>): The buffer_head that
                  initiated this bio.
                - decoder (gdb.Value<void (*)(struct buffer_head *, int)>):
                  A decoder for the buffer head
        """
        bh = bio['bi_private'].cast(cls.buffer_head_p_type)
        chain = {
            'description' :
                "{:x} bio: Bio representation of buffer head".format(int(bio)),
            'bio' : bio,
            'next' : bh,
            'decoder' : cls.decode_buffer_head,
        }

        return chain

    @classmethod
    def decode_buffer_head(cls, bh):
        """
        Decodes a struct buffer_head

        This method decodes a struct buffer_head, using an
        implementation-specific decoder, if available

        Args:
            bio(gdb.Value<struct buffer_head>): The struct buffer_head to be
                decoded.

        Returns:
            dict: Minimally contains the following items.
                - description (str): Human-readable description of the bio
                - bh (gdb.Value<struct buffer_head>): The struct buffer_head
                Additional items may be available based on the
                implmentation-specific decoder.
        """
        endio = bh['b_end_io']
        try:
            return cls.buffer_head_decoders[endio](bh)
        except KeyError:
            pass
        desc = "{:x} buffer_head: for dev {}, block {}, size {} (undecoded)".format(
                    int(bh), block_device_name(bh['b_bdev']),
                    bh['b_blocknr'], bh['b_size'])
        chain = {
            'description' : desc,
            'bh' : bh,
        }
        return chain

    @classmethod
    def decode_end_buffer_write_sync(cls, bh):
        """
        Decodes a struct buffer_head submitted by file systems for routine
        synchronous writeback.

        Args:
            bio(gdb.Value<struct buffer_head>): The struct buffer_head to be
                decoded.

        Returns:
            dict: Minimally contains the following items.
                - description (str): Human-readable description of the bio
                - bh (gdb.Value<struct buffer_head>): The struct buffer_head
        """
        desc = ("{:x} buffer_head: for dev {}, block {}, size {} (unassociated)"
                .format(block_device_name(bh['b_bdev']),
                        bh['b_blocknr'], bh['b_size']))
        chain = {
            'description' : desc,
            'bh' : bh,
        }
        return chain

    @export
    @classmethod
    def for_each_super_block(cls) -> Iterable[gdb.Value]:
        """
        Iterate over the list of super blocks and yield each one.

        Args:
            None

        Yields:
            gdb.Value<struct super_block>
        """
        for sb in list_for_each_entry(cls.super_blocks, cls.super_block_type,
                                      's_list'):
            yield sb

    @export
    @classmethod
    def get_super_block(cls, desc: AddressSpecifier,
                        force: bool=False) -> gdb.Value:
        """
        Given an address description return a gdb.Value that contains
        a struct super_block at that address.

        Args:
            desc (gdb.Value, str, or int): The address for which to provide
                a casted pointer
            force (bool): Skip testing whether the value is available.

        Returns:
            gdb.Value<struct super_block>: The super_block at the requested
                location

        Raises:
            gdb.NotAvailableError: The target value was not available.
        """
        sb = get_typed_pointer(desc, cls.super_block_type).dereference()
        if not force:
            try:
                x = int(sb['s_dev'])
            except gdb.NotAvailableError:
                raise gdb.NotAvailableError(f"no superblock available at `{desc}'")
        return sb

inst = FileSystem()
