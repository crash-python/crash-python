#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
from crash.types.list import list_for_each_entry
from crash.util import container_of
import gdb

# This script dumps the inodes and buffers in the XFS AIL.  The mount
# address is hard-coded and would need to be replaced for use.

XFS_LI_EFI              = 0x1236
XFS_LI_EFD              = 0x1237
XFS_LI_IUNLINK          = 0x1238
XFS_LI_INODE            = 0x123b  # aligned ino chunks, var-size ibufs
XFS_LI_BUF              = 0x123c  # v2 bufs, variable sized inode bufs
XFS_LI_DQUOT            = 0x123d
XFS_LI_QUOTAOFF         = 0x123e

XFS_LI_TYPES = {
    XFS_LI_EFI : "XFS_LI_EFI",
    XFS_LI_EFD : "XFS_LI_EFD",
    XFS_LI_IUNLINK : "XFS_LI_IUNLINK",
    XFS_LI_INODE : "XFS_LI_INODE",
    XFS_LI_BUF : "XFS_LI_BUF",
    XFS_LI_EFI : "XFS_LI_EFI",
    XFS_LI_DQUOT : "XFS_LI_DQUOT",
    XFS_LI_QUOTAOFF : "XFS_LI_QUOTAOFF",
}

def xfs_for_each_ail_entry(ail):
    xfs_log_item_type = gdb.lookup_type('struct xfs_log_item')
    for item in list_for_each_entry(ail['xa_ail'], xfs_log_item_type, 'li_ail'):
        yield item

def xfs_for_each_ail_log_item(mp):
    for item in for_each_ail_entry(mp['m_ail']):
        yield item

xfs_buf_log_item_type = gdb.lookup_type('struct xfs_buf_log_item')
xfs_inode_log_item_type = gdb.lookup_type('struct xfs_inode_log_item')
xfs_efi_log_item_type = gdb.lookup_type('struct xfs_efi_log_item')
xfs_efd_log_item_type = gdb.lookup_type('struct xfs_efd_log_item')
xfs_dq_logitem_type = gdb.lookup_type('struct xfs_dq_logitem')
xfs_qoff_logitem_type = gdb.lookup_type('struct xfs_qoff_logitem')

def xfs_for_each_ail_log_item_typed(mp):
    for item in for_each_xfs_ail_item(mp):
        li_type = long(item['li_type'])
        if li_type == XFS_LI_BUF:
            yield container_of(item, xfs_buf_log_item_type, 'bli_item')
        elif li_type == XFS_LI_INODE:
            yield container_of(item, xfs_inode_log_item_type, 'ili_item')
        elif li_type == XFS_LI_EFI:
            yield container_of(item, xfs_efi_log_item_type, 'efi_item')
        elif li_type == XFS_LI_EFD:
            yield container_of(item, xfs_efd_log_item_type, 'efd_item')
        elif li_type == XFS_LI_IUNLINK:
            yield li_type
        elif li_type == XFS_LI_DQUOT:
            yield container_of(item, xfs_dq_logitem, 'qli_item')
        elif li_type == XFS_LI_QUOTAOFF:
            yield container_of(item, xfs_qoff_logitem, 'qql_item')
        else:
            print XFS_LI_TYPES[li_type]

xfs_mount = gdb.lookup_type('struct xfs_mount').pointer()
mp = gdb.Value(0xffff880bf34a1800).cast(xfs_mount).dereference()

for item in xfs_for_each_ail_log_item_typed(mp):
    if item.type == xfs_buf_log_item_type:
        buf = item['bli_buf']
        print "xfs_buf @ {:x} blockno={}".format(long(buf), buf['b_bn'])
    elif item.type == xfs_inode_log_item_type:
        xfs_inode = item['ili_inode']
        print "inode @ {:x}".format(long(xfs_inode['i_vnode'].address))
    else:
        print "{} @ {:x}".format(item.type, long(item.address))
