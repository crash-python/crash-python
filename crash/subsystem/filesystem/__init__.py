# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable, Union

from crash.util import container_of, get_typed_pointer, decode_flags
from crash.util.symbols import Types, Symvals
from crash.infra.lookup import DelayedSymval, DelayedType
from crash.types.list import list_for_each_entry
from crash.subsystem.storage import block_device_name

import gdb

types = Types('struct super_block')
symvals = Symvals('super_blocks')

AddressSpecifier = Union[int, str, gdb.Value]

MS_RDONLY = 1
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_SYNCHRONOUS = 16
MS_REMOUNT = 32
MS_MANDLOCK = 64
MS_DIRSYNC = 128
MS_NOATIME = 1024
MS_NODIRATIME = 2048
MS_BIND = 4096
MS_MOVE = 8192
MS_REC = 16384
MS_VERBOSE = 32768
MS_SILENT = 32768
MS_POSIXACL = (1<<16)
MS_UNBINDABLE = (1<<17)
MS_PRIVATE = (1<<18)
MS_SLAVE = (1<<19)
MS_SHARED = (1<<20)
MS_RELATIME = (1<<21)
MS_KERNMOUNT = (1<<22)
MS_I_VERSION = (1<<23)
MS_STRICTATIME = (1<<24)
MS_LAZYTIME = (1<<25)
MS_NOSEC = (1<<28)
MS_BORN = (1<<29)
MS_ACTIVE = (1<<30)
MS_NOUSER = (1<<31)

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

def super_fstype(sb: gdb.Value) -> str:
    """
    Returns the file system type's name for a given superblock.

    Args:
        sb: The ``struct super_block`` for which to return the file system
            type's name.  The value must be of type ``struct super_block``.

    Returns:
        :obj:`str`:The file system type's name

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return sb['s_type']['name'].string()

def super_flags(sb: gdb.Value) -> str:
    """
    Returns the flags associated with the given superblock.

    Args:
        sb: The ``struct super_block`` for which to return the flags.
            The value must be of type ``struct super_block``.

    Returns:
        :obj:`str`:The flags field in human-readable form.

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return decode_flags(sb['s_flags'], SB_FLAGS)

def for_each_super_block() -> Iterable[gdb.Value]:
    """
    Iterate over the list of super blocks and yield each one.

    Yields:
        :obj:`gdb.Value`: One value for each super block.  Each value
        will be of type ``struct super_block``.

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    for sb in list_for_each_entry(symvals.super_blocks,
                                  types.super_block_type, 's_list'):
        yield sb

def get_super_block(desc: AddressSpecifier, force: bool = False) -> gdb.Value:
    """
    Given an address description return a gdb.Value that contains
    a struct super_block at that address.

    Args:
        desc: The address for which to provide a casted pointer.  The address
            may be specified using an existing Value, an integer address,
            or a hexadecimal address represented as a 0x-prefixed string.
        force: Skip testing whether the value is available.

    Returns:
        :obj:`gdb.Value`: The super block at the requested location.
        The value will be ``struct super_block``.

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    sb = get_typed_pointer(desc, types.super_block_type).dereference()
    if not force:
        try:
            x = int(sb['s_dev'])
        except gdb.NotAvailableError:
            raise gdb.NotAvailableError(f"no superblock available at `{desc}'")

    return sb

def is_fstype_super(super_block: gdb.Value, name: str) -> bool:
    """
    Tests whether the super_block belongs to a particular file system type.

    This uses a naive string comparison so modules are not required.

    Args:
        super_block: The struct super_block to test.  The value must be
            of type ``struct super_block``.
        name: The name of the file system type

    Returns:
        :obj:`bool`: whether the ``struct super_block`` belongs to the
        specified file system

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return super_fstype(super_block) == name

def is_fstype_inode(inode: gdb.Value, name: str) -> bool:
    """
    Tests whether the inode belongs to a particular file system type.

    Args:
        inode: The struct inode to test.  The value must be of
            type ``struct inode``.
        name: The name of the file system type

    Returns:
        :obj:`bool`: whether the inode belongs to the specified file system

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return is_fstype_super(inode['i_sb'], name)
