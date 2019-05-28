# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable

import gdb
from gdb.types import get_basic_type

from crash.util import container_of
from crash.util.symbols import Types, Symvals, SymbolCallbacks, TypeCallbacks
from crash.types.classdev import for_each_class_device
from . import decoders
from crash.exceptions import DelayedAttributeError, InvalidArgumentError

types = Types([ 'struct gendisk', 'struct hd_struct', 'struct device',
                  'struct device_type', 'struct bdev_inode' ])
symvals = Symvals([ 'block_class', 'blockdev_superblock', 'disk_type',
                    'part_type' ])

def for_each_bio_in_stack(bio: gdb.Value) -> Iterable[decoders.Decoder]:
    """
    Iterates and decodes each bio involved in a stacked storage environment

    This method will yield a Decoder object describing each level
    in the storage stack, starting with the provided bio, as
    processed by each level's decoder.  The stack will be interrupted
    if an encountered object doesn't have a decoder specified.

    See crash.subsystem.storage.decoders for more detail.

    Args:
        bio (gdb.Value<struct bio>): The initial struct bio to start
            decoding

    Yields:
        Decoder
    """
    decoder = decoders.decode_bio(bio)
    while decoder is not None:
        yield decoder
        decoder = next(decoder)

def dev_to_gendisk(dev: gdb.Value) -> gdb.Value:
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
    return container_of(dev, types.gendisk_type, 'part0.__dev')

def dev_to_part(dev: gdb.Value) -> gdb.Value:
    """
    Converts a struct device that is embedded in a struct hd_struct
    back to the struct hd_struct.

    Args:
        dev (gdb.Value<struct device>): A struct device embedded within a
            struct hd_struct.  No checking is performed.  Results if other
            structures are provided are undefined.

    Returns:
        gdb.Value<struct hd_struct>: The converted struct hd_struct

    """
    return container_of(dev, types.hd_struct_type, '__dev')

def gendisk_to_dev(gendisk: gdb.Value) -> gdb.Value:
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

def part_to_dev(part: gdb.Value) -> gdb.Value:
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


def for_each_block_device(subtype: gdb.Value=None) -> Iterable[gdb.Value]:
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
        gdb.Value<struct gendisk> or
        gdb.Value<struct hd_struct>:
            A struct gendisk or struct hd_struct that meets
            the filter criteria.

    Raises:
        RuntimeError: An unknown device type was encountered during
            iteration.
    """

    if subtype:
        if get_basic_type(subtype.type) == types.device_type_type:
            subtype = subtype.address
        elif get_basic_type(subtype.type) != types.device_type_type.pointer():
            raise InvalidArgumentError("subtype must be {} not {}"
                            .format(types.device_type_type.pointer(),
                                    subtype.type.unqualified()))
    for dev in for_each_class_device(symvals.block_class, subtype):
        if dev['type'] == symvals.disk_type.address:
            yield dev_to_gendisk(dev)
        elif dev['type'] == symvals.part_type.address:
            yield dev_to_part(dev)
        else:
            raise RuntimeError("Encountered unexpected device type {}"
                               .format(dev['type']))

def for_each_disk() -> Iterable[gdb.Value]:
    """
    Iterates over each block device registered with the block class
    that corresponds to an entire disk.

    This is an alias for for_each_block_device(disk_type)
    """

    return for_each_block_device(symvals.disk_type)

def gendisk_name(gendisk: gdb.Value) -> str:
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
        InvalidArgumentError: gdb.Value does not describe a struct gendisk or
            struct hd_struct
    """
    if gendisk.type.code == gdb.TYPE_CODE_PTR:
        gendisk = gendisk.dereference()

    if get_basic_type(gendisk.type) == types.gendisk_type:
        return gendisk['disk_name'].string()
    elif get_basic_type(gendisk.type) == types.hd_struct_type:
        parent = dev_to_gendisk(part_to_dev(gendisk)['parent'])
        return "{}{:d}".format(gendisk_name(parent), int(gendisk['partno']))
    else:
        raise InvalidArgumentError("expected {} or {}, not {}"
                        .format(types.gendisk_type, types.hd_struct_type,
                        gendisk.type.unqualified()))

def block_device_name(bdev: gdb.Value) -> str:
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
    return gendisk_name(bdev['bd_disk'])

def is_bdev_inode(inode: gdb.Value) -> bool:
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
    return inode['i_sb'] == symvals.blockdev_superblock

def inode_to_block_device(inode: gdb.Value) -> gdb.Value:
    """
    Returns the block device associated with this inode.

    If the inode describes a block device, return that block device.
    Otherwise, raise InvalidArgumentError.

    Args:
        inode(gdb.Value<struct inode>): The struct inode for which to
            return the associated block device

    Returns:
        gdb.Value<struct block_device>: The struct block_device associated
            with the provided struct inode

    Raises:
        InvalidArgumentError: inode does not describe a block device
    """
    if inode['i_sb'] != symvals.blockdev_superblock:
        raise InvalidArgumentError("inode does not correspond to block device")
    return container_of(inode, types.bdev_inode_type, 'vfs_inode')['bdev']

def inode_on_bdev(inode: gdb.Value) -> gdb.Value:
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
    if is_bdev_inode(inode):
        return inode_to_block_device(inode)
    else:
        return inode['i_sb']['s_bdev']

def _check_types(result):
    try:
        if symvals.part_type.type.unqualified() != types.device_type_type:
            raise TypeError("part_type expected to be {} not {}"
                            .format(symvals.device_type_type,
                                    types.part_type.type))

        if symvals.disk_type.type.unqualified() != types.device_type_type:
            raise TypeError("disk_type expected to be {} not {}"
                            .format(symvals.device_type_type,
                                    types.disk_type.type))
    except DelayedAttributeError:
        pass

symbol_cbs = SymbolCallbacks([ ( 'disk_type', _check_types ),
                               ( 'part_type', _check_types )] )
type_cbs = TypeCallbacks([ ('struct device_type', _check_types ) ])
