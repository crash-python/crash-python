# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb

from crash.infra import CrashBaseClass

class BtrfsFileSystem(CrashBaseClass):
    __types__ = [ 'struct btrfs_inode', 'struct btrfs_fs_info *' ]

    @classmethod
    def btrfs_inode(cls, vfs_inode):
        """
        Converts a VFS inode to a btrfs inode

        This method converts a struct inode to a struct btrfs_inode.

        Args:
            vfs_inode (gdb.Value<struct inode>): The struct inode to convert
                to a struct btrfs_inode

        Returns:
            gdb.Value<struct btrfs_inode>: The converted struct btrfs_inode
        """
        return container_of(vfs_inode, cls.btrfs_inode_type, 'vfs_inode')

    @classmethod
    def btrfs_sb_info(cls, super_block):
        """
        Converts a VFS superblock to a btrfs fs_info

        This method converts a struct super_block to a struct btrfs_fs_info

        Args:
            super_block (gdb.Value<struct super_block>): The struct super_block
                to convert to a struct btrfs_fs_info.

        Returns:
            gdb.Value<struct btrfs_fs_info>: The converted struct
                btrfs_fs_info
        """
        return super_block['s_fs_info'].cast(cls.btrfs_fs_info_p_type)
