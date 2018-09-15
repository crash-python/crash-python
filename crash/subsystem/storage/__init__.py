# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import gdb
import sys

if sys.version_info.major >= 3:
    long = int

from crash.util import container_of
from crash.infra import CrashBaseClass, export
from crash.types.classdev import for_each_class_device
import crash.exceptions

class Storage(CrashBaseClass):
    __types__ = [ 'struct gendisk',
                  'struct hd_struct',
                  'struct device',
                  'struct device_type',
                  'struct bdev_inode' ]
    __symvals__ = [ 'block_class',
                    'blockdev_superblock',
                    'disk_type',
                    'part_type' ]
    __symbol_callbacks = [
                ( 'disk_type', '_check_types' ),
                ( 'part_type', '_check_types' ) ]
    __type_callbacks__ = [ ('struct device_type', '_check_types' ) ]

    bio_decoders = {}

    @classmethod
    def _check_types(cls, result):
        try:
            if cls.part_type.type.unqualified() != cls.device_type_type:
                raise TypeError("part_type expected to be {} not {}"
                                .format(cls.device_type_type,
                                        cls.part_type.type))

            if cls.disk_type.type.unqualified() != cls.device_type_type:
                raise TypeError("disk_type expected to be {} not {}"
                                .format(cls.device_type_type,
                                        cls.disk_type.type))
            cls.types_checked = True
        except crash.exceptions.DelayedAttributeError:
            pass

    @export
    @classmethod
    def register_bio_decoder(cls, sym, decoder):
        """
        Registers a bio decoder with the storage subsystem.

        A bio decoder is a method that accepts a bio, potentially
        interprets the private members of the bio, and returns
        a dictionary.  The only mandatory member of the dictionary
        is 'description' which contains a human-readable description
        of the purpose of this bio.

        If the bio is part of a stack, the 'next' item should contain
        the next object in the stack.  It does not necessarily need
        to be a bio.  It does need to have a 'decoder' item declared
        that will accept the given object.  The decoder does not
        need to be registered unless it will be a top-level decoder.

        Other items can be added as-needed to allow informed callers
        to obtain direct information.

        Args:
            sym (gdb.Symbol or gdb.Value<void (*)(struct bio *)>):
                The Symbol or Value describing a kernel function used as
                a bio->b_end_io callback
            decoder (method): A Python method that accepts a
                gdb.Value(struct bio)

        Raises:
            TypeError: sym is not a gdb.Symbol or gdb.Value
        """

        if isinstance(sym, gdb.Symbol):
            sym = sym.value().address
        elif not isinstance(sym, gdb.Value):
            raise TypeError("register_bio_decoder expects gdb.Symbol or gdb.Value")
        cls.bio_decoders[long(sym)] = decoder

    @export
    @classmethod
    def for_each_bio_in_stack(cls, bio):
        """
        Iterates and decodes each bio involved in a stacked storage environment

        This method will return a dictionary describing each object
        in the storage stack, starting with the provided bio, as
        processed by each level's decoder.  The stack will be interrupted
        if an encountered object doesn't have a decoder specified.

        See register_bio_decoder for more detail.

        Args:
            bio (gdb.Value<struct bio>): The initial struct bio to start
                decoding

        Yields:
            dict : Contains, minimally, the following item.
                - description (str): A human-readable description of the bio.
                  Additional items may be available based on the
                  implmentation-specific decoder.
        """
        first = cls.bio_decoders[long(bio['bi_end_io'])](bio)
        if first:
            yield first
            while 'decoder' in first:
                first = first['decoder'](first['next'])
                yield first

    @export
    @classmethod
    def decode_bio(cls, bio):
        """
        Decodes a single bio, if possible

        This method will return a dictionary describing a single bio
        after decoding it using a registered decoder, if available.

        If no decoder is registered, a generic description will be
        returned in the dictionary's 'description' field.

        Args:
            bio (gdb.Value<struct bio>): The bio to decode

        Returns:
            dict: Contains, minimally, the following item.
                - description (str): A human-readable description of the bio.
                  Additional items may be available based on the
                  implmentation-specific decoder.
        """

        try:
            return cls.bio_decoders[long(bio['bi_end_io'])](bio)
        except KeyError:
            chain = {
                'description' : "{:x} bio: undecoded bio on {} ({})".format(
                    long(bio), block_device_name(bio['bi_bdev']),
                    bio['bi_end_io']),
            }
            return chain

    @export
    def dev_to_gendisk(self, dev):
        """
        Converts a struct device that is embedded in a struct gendisk
        back to the struct gendisk.

        Args:
            dev (gdb.Value<struct device>) : A struct device contained within
                  a struct gendisk.  No checking is performed.  Results
                  if other structures are provided are undefined.

        Returns:
            gdb.Value<struct hd_struct> : The converted struct hd_struct
        """
        return container_of(dev, self.gendisk_type, 'part0.__dev')

    @export
    def dev_to_part(self, dev):
        """
        Converts a struct device that is embedded in a struct hd_struct
        back to the struct hd_struct.

        Args:
            dev (gdb.Value<struct device>): A struct device embedded within a
                struct hd_struct.  No checking is performed.  Results if other
                structures are provided are undefined.

        Returns:
            gdb.Value(struct hd_struct): The converted struct hd_struct

        """
        return container_of(dev, self.hd_struct_type, '__dev')

    @export
    def gendisk_to_dev(self, gendisk):
        """
        Converts a struct gendisk that embeds a struct device to
        the struct device.

        Args:
            dev (gdb.Value<struct gendisk>): A struct gendisk that embeds
                a struct device.  No checking is performed.  Results
                if other structures are provided are undefined.

        Returns:
            gdb.Value<struct device>: The converted struct device
        """

        return gendisk['part0']['__dev'].address

    @export
    def part_to_dev(self, part):
        """
        Converts a struct hd_struct that embeds a struct device to
        the struct device.

        Args:
            dev (gdb.Value<struct hd_struct>): A struct hd_struct that embeds
                a struct device.  No checking is performed.  Results if
                other structures are provided are undefined.

        Returns:
            gdb.Value<struct device>: The converted struct device
        """
        return part['__dev'].address

    @export
    def for_each_block_device(self, subtype=None):
        """
        Iterates over each block device registered with the block class.

        This method iterates over the block_class klist and yields every
        member found.  The members are either struct gendisk or
        struct hd_struct, depending on whether it describes an entire
        disk or a partition, respectively.

        The members can be filtered by providing a subtype, which
        corresponds to a the the type field of the struct device.

        Args:
            subtype (gdb.Value<struct device_type>, optional): The struct
                device_type that will be used to match and filter.  Typically
                'disk_type' or 'device_type'

        Yields:
            gdb.Value<struct gendisk or struct hd_struct> - A struct gendisk
                or struct hd_struct that meets the filter criteria.

        Raises:
            RuntimeError: An unknown device type was encountered during
                iteration.
        """

        if subtype:
            if subtype.type.unqualified() == self.device_type_type:
                subtype = subtype.address
            elif subtype.type.unqualified() != self.device_type_type.pointer():
                raise TypeError("subtype must be {} not {}"
                                .format(self.device_type_type.pointer(),
                                        subtype.type.unqualified()))
        for dev in for_each_class_device(self.block_class, subtype):
            if dev['type'] == self.disk_type.address:
                yield self.dev_to_gendisk(dev)
            elif dev['type'] == self.part_type.address:
                yield self.dev_to_part(dev)
            else:
                raise RuntimeError("Encountered unexpected device type {}"
                                   .format(dev['type']))

    @export
    def for_each_disk(self):
        """
        Iterates over each block device registered with the block class
        that corresponds to an entire disk.

        This is an alias for for_each_block_device(disk_type)
        """

        return self.for_each_block_device(self.disk_type)

    @export
    def gendisk_name(self, gendisk):
        """
        Returns the name of the provided block device.

        This method evaluates the block device and returns the name,
        including partition number, if applicable.

        Args:
            gendisk(gdb.Value<struct gendisk or struct hd_struct>):
                A struct gendisk or struct hd_struct for which to return
                the name

        Returns:
            str: the name of the block device

        Raises:
            TypeError: gdb.Value does not describe a struct gendisk or
                struct hd_struct
        """
        if gendisk.type.code == gdb.TYPE_CODE_PTR:
            gendisk = gendisk.dereference()

        if gendisk.type.unqualified() == self.gendisk_type:
            return gendisk['disk_name'].string()
        elif gendisk.type.unqualified() == self.hd_struct_type:
            parent = self.dev_to_gendisk(self.part_to_dev(gendisk)['parent'])
            return "{}{:d}".format(self.gendisk_name(parent),
                                   int(gendisk['partno']))
        else:
            raise TypeError("expected {} or {}, not {}"
                            .format(self.gendisk_type, self.hd_struct_type,
                            gendisk.type.unqualified()))

    @export
    def block_device_name(self, bdev):
        """
        Returns the name of the provided block device.

        This method evaluates the block device and returns the name,
        including partition number, if applicable.

        Args:
            bdev(gdb.Value<struct block_device>): A struct block_device for
                which to return the name

        Returns:
            str: the name of the block device
        """
        return self.gendisk_name(bdev['bd_disk'])

    @export
    def is_bdev_inode(self, inode):
        """
        Tests whether the provided struct inode describes a block device

        This method evaluates the inode and returns a True or False,
        depending on whether the inode describes a block device.

        Args:
            bdev(gdb.Value<struct inode>): The struct inode to test whether
                it describes a block device.

        Returns:
            bool: True if the inode describes a block device, False otherwise.
        """
        return inode['i_sb'] == self.blockdev_superblock

    @export
    def inode_to_block_device(self, inode):
        """
        Returns the block device associated with this inode.

        If the inode describes a block device, return that block device.
        Otherwise, raise TypeError.

        Args:
            inode(gdb.Value<struct inode>): The struct inode for which to
                return the associated block device

        Returns:
            gdb.Value<struct block_device>: The struct block_device associated
                with the provided struct inode

        Raises:
            TypeError: inode does not describe a block device
        """
        if inode['i_sb'] != self.blockdev_superblock:
            raise TypeError("inode does not correspond to block device")
        return container_of(inode, self.bdev_inode_type, 'vfs_inode')['bdev']

    @export
    def inode_on_bdev(self, inode):
        """
        Returns the block device associated with this inode.

        If the inode describes a block device, return that block device.
        Otherwise, return the block device, if any, associated
        with the inode's super block.

        Args:
            inode(gdb.Value<struct inode>): The struct inode for which to
                return the associated block device

        Returns:
            gdb.Value<struct block_device>: The struct block_device associated
                with the provided struct inode
        """
        if self.is_bdev_inode(inode):
            return self.inode_to_block_device(inode)
        else:
            return inode['i_sb']['s_bdev']
inst = Storage()
