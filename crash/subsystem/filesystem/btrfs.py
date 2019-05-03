# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.util.symbols import Types

types = Types([ 'struct btrfs_inode', 'struct btrfs_fs_info *',
                  'struct btrfs_fs_info' ])

def btrfs_inode(vfs_inode):
    """
    Converts a VFS inode to a btrfs inode

    This method converts a struct inode to a struct btrfs_inode.

    Args:
        vfs_inode (gdb.Value<struct inode>): The struct inode to convert
            to a struct btrfs_inode

    Returns:
        gdb.Value<struct btrfs_inode>: The converted struct btrfs_inode
    """
    return container_of(vfs_inode, types.btrfs_inode_type, 'vfs_inode')

def btrfs_fs_info(super_block):
    """
    Converts a VFS superblock to a btrfs fs_info

    This method converts a struct super_block to a struct btrfs_fs_info

    Args:
        super_block (gdb.Value<struct super_block>): The struct super_block
            to convert to a struct btrfs_fs_info.

    Returns:
        gdb.Value<struct btrfs_fs_info *>: The converted struct
            btrfs_fs_info
    """
    return super_block['s_fs_info'].cast(types.btrfs_fs_info_p_type)
