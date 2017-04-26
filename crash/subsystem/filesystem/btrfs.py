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
        return container_of(vfs_inode, cls.btrfs_inode_type, 'vfs_inode')

    @classmethod
    def btrfs_sb_info(cls, super_block):
        return super_block['s_fs_info'].cast(cls.btrfs_fs_info_p_type)
