# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import uuid

from crash.exceptions import InvalidArgumentError
from crash.util import decode_uuid, struct_has_member, container_of
from crash.util.symbols import Types
from crash.subsystem.filesystem import is_fstype_super

types = Types(['struct btrfs_inode', 'struct btrfs_fs_info *',
               'struct btrfs_fs_info'])

def is_btrfs_super(super_block: gdb.Value) -> bool:
    """
    Tests whether a ``struct super_block`` belongs to btrfs.

    Args:
        super_block: The ``struct super_block`` to test.
            The value must be of type ``struct super_block``.

    Returns:
        :obj:`bool`: Whether the super_block belongs to btrfs

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return is_fstype_super(super_block, "btrfs")

def is_btrfs_inode(vfs_inode: gdb.Value) -> bool:
    """
    Tests whether a inode belongs to btrfs.

    Args:
        vfs_inode: The ``struct inode`` to test.  The value must be
            of type ``struct inode``.

    Returns:
        :obj:`bool`: Whether the inode belongs to btrfs

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return is_btrfs_super(vfs_inode['i_sb'])

def btrfs_inode(vfs_inode: gdb.Value, force: bool = False) -> gdb.Value:
    """
    Converts a VFS inode to a btrfs inode

    This method converts a ``struct inode`` to a ``struct btrfs_inode``.

    Args:
        vfs_inode: The ``struct inode`` to convert to a ``struct btrfs_inode``.
            The value must be of type ``struct inode``.

        force: Ignore type checking.

    Returns:
        :obj:`gdb.Value`: The converted ``struct btrfs_inode``.
        The value will be of type ``struct btrfs_inode``.

    Raises:
        :obj:`.InvalidArgumentError`: the inode does not belong to btrfs
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if not force and not is_btrfs_inode(vfs_inode):
        raise InvalidArgumentError("inode does not belong to btrfs")

    return container_of(vfs_inode, types.btrfs_inode_type, 'vfs_inode')

def btrfs_fs_info(super_block: gdb.Value, force: bool = False) -> gdb.Value:
    """
    Resolves a btrfs_fs_info from  a VFS superblock

    This method resolves a struct btrfs_fs_info from a struct super_block

    Args:
        super_block: The ``struct super_block`` to use to resolve a'
            ``struct btrfs_fs_info``.  A pointer to a ``struct super_block``
            is also acceptable.

        force: Ignore type checking.

    Returns:
        :obj:`gdb.Value: The resolved ``struct btrfs_fs_info``.  The value will
        be of type ``struct btrfs_fs_info``.

    Raises:
        :obj:`.InvalidArgumentError`: the super_block does not belong to btrfs
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if not force and not is_btrfs_super(super_block):
        raise InvalidArgumentError("super_block does not belong to btrfs")

    fs_info = super_block['s_fs_info'].cast(types.btrfs_fs_info_p_type)
    return fs_info.dereference()

def btrfs_fsid(super_block: gdb.Value, force: bool = False) -> uuid.UUID:
    """
    Returns the btrfs fsid (UUID) for the specified superblock.

    Args:
        super_block: The ``struct super_block`` for which to return the
            btrfs fsid.  The value must be of type ``struct super_block``.

        force: Ignore type checking.

    Returns:
        :obj:`uuid.UUID`: The Python UUID Object for the btrfs fsid

    Raises:
        :obj:`.InvalidArgumentError`: the super_block does not belong to btrfs
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    fs_info = btrfs_fs_info(super_block, force)
    if struct_has_member(types.btrfs_fs_info_type, 'fsid'):
        return decode_uuid(fs_info['fsid'])
    return decode_uuid(fs_info['fs_devices']['fsid'])

def btrfs_metadata_uuid(sb: gdb.Value, force: bool = False) -> uuid.UUID:
    """
    Returns the btrfs metadata uuid for the specified superblock.

    Args:
        super_block: The ``struct super_block`` for which to return the
            btrfs metadata uuid.  The value must be of type
            ``struct super_block``.

        force: Ignore type checking.

    Returns:
        :obj:`uuid.UUID`: The Python UUID Object for the btrfs fsid

    Raises:
        :obj:`.InvalidArgumentError`: the super_block does not belong to btrfs
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    fs_info = btrfs_fs_info(sb, force)
    if struct_has_member(types.btrfs_fs_info_type, 'metadata_uuid'):
        return decode_uuid(fs_info['metadata_uuid'])
    elif struct_has_member(fs_info['fs_devices'].type, 'metadata_uuid'):
        return decode_uuid(fs_info['fs_devices']['metadata_uuid'])
    else:
        return btrfs_fsid(sb, force)
