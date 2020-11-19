# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
The crash.subsystem.filesystem.xfs module offers helpers to work with
XFS file systems.
"""

from typing import Iterable, Any

import uuid

import gdb

from crash.exceptions import InvalidArgumentError
from crash.types.list import list_for_each_entry
from crash.util import container_of, decode_uuid_t, decode_flags
from crash.util import struct_has_member
from crash.util.symbols import Types, TypeCallbacks
from crash.subsystem.filesystem import is_fstype_super, is_fstype_inode
from crash.subsystem.storage import block_device_name
from crash.subsystem.storage.decoders import Decoder

# XFS inode locks
XFS_IOLOCK_EXCL = 0x01
XFS_IOLOCK_SHARED = 0x02
XFS_ILOCK_EXCL = 0x04
XFS_ILOCK_SHARED = 0x08
XFS_MMAPLOCK_EXCL = 0x10
XFS_MMAPLOCK_SHARED = 0x20

XFS_LOCK_MASK = 0x3f

XFS_LOCK_FLAGS = {
    XFS_IOLOCK_EXCL     : "XFS_IOLOCK_EXCL",
    XFS_IOLOCK_SHARED   : "XFS_IOLOCK_SHARED",
    XFS_ILOCK_EXCL      : "XFS_ILOCK_EXCL",
    XFS_ILOCK_SHARED    : "XFS_ILOCK_SHARED",
    XFS_MMAPLOCK_EXCL   : "XFS_MMAPLOCK_EXCL",
    XFS_MMAPLOCK_SHARED : "XFS_MMAPLOCK_SHARED",
}

XFS_LI_EFI = 0x1236
XFS_LI_EFD = 0x1237
XFS_LI_IUNLINK = 0x1238
XFS_LI_INODE = 0x123b  # aligned ino chunks, var-size ibufs
XFS_LI_BUF = 0x123c  # v2 bufs, variable sized inode bufs
XFS_LI_DQUOT = 0x123d
XFS_LI_QUOTAOFF = 0x123e

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

XFS_BLI_HOLD = 0x01
XFS_BLI_DIRTY = 0x02
XFS_BLI_STALE = 0x04
XFS_BLI_LOGGED = 0x08
XFS_BLI_INODE_ALLOC_BUF = 0x10
XFS_BLI_STALE_INODE = 0x20
XFS_BLI_INODE_BUF = 0x40

XFS_BLI_FLAGS = {
    XFS_BLI_HOLD              :         "HOLD",
    XFS_BLI_DIRTY             :        "DIRTY",
    XFS_BLI_STALE             :        "STALE",
    XFS_BLI_LOGGED            :       "LOGGED",
    XFS_BLI_INODE_ALLOC_BUF   : "INODE_ALLOC",
    XFS_BLI_STALE_INODE       :  "STALE_INODE",
    XFS_BLI_INODE_BUF         :    "INODE_BUF",
}

XBF_READ = (1 << 0)  # buffer intended for reading from device
XBF_WRITE = (1 << 1)  # buffer intended for writing to device
XBF_MAPPED = (1 << 2)  # buffer mapped (b_addr valid)
XBF_ASYNC = (1 << 4)  # initiator will not wait for completion
XBF_DONE = (1 << 5)  # all pages in the buffer uptodate
XBF_DELWRI = (1 << 6)  # buffer has dirty pages
XBF_STALE = (1 << 7)  # buffer has been staled, do not find it
XBF_ORDERED = (1 << 11) # use ordered writes
XBF_READ_AHEAD = (1 << 12) # asynchronous read-ahead
XBF_LOG_BUFFER = (1 << 13) # this is a buffer used for the log

# flags used only as arguments to access routines
XBF_LOCK = (1 << 14) # lock requested
XBF_TRYLOCK = (1 << 15) # lock requested, but do not wait
XBF_DONT_BLOCK = (1 << 16) # do not block in current thread

# flags used only internally
_XBF_PAGES = (1 << 18) # backed by refcounted pages
_XBF_RUN_QUEUES = (1 << 19) # run block device task queue
_XBF_KMEM = (1 << 20) # backed by heap memory
_XBF_DELWRI_Q = (1 << 21) # buffer on delwri queue
_XBF_LRU_DISPOSE = (1 << 24) # buffer being discarded

XFS_BUF_FLAGS = {
    XBF_READ             : "READ",
    XBF_WRITE            : "WRITE",
    XBF_MAPPED           : "MAPPED",
    XBF_ASYNC            : "ASYNC",
    XBF_DONE             : "DONE",
    XBF_DELWRI           : "DELWRI",
    XBF_STALE            : "STALE",
    XBF_ORDERED          : "ORDERED",
    XBF_READ_AHEAD       : "READ_AHEAD",
    XBF_LOCK             : "LOCK",       # should never be set
    XBF_TRYLOCK          : "TRYLOCK",    # ditto
    XBF_DONT_BLOCK       : "DONT_BLOCK", # ditto
    _XBF_PAGES           : "PAGES",
    _XBF_RUN_QUEUES      : "RUN_QUEUES",
    _XBF_KMEM            : "KMEM",
    _XBF_DELWRI_Q        : "DELWRI_Q",
    _XBF_LRU_DISPOSE     : "LRU_DISPOSE",
}

XFS_ILOG_CORE = 0x001
XFS_ILOG_DDATA = 0x002
XFS_ILOG_DEXT = 0x004
XFS_ILOG_DBROOT = 0x008
XFS_ILOG_DEV = 0x010
XFS_ILOG_UUID = 0x020
XFS_ILOG_ADATA = 0x040
XFS_ILOG_AEXT = 0x080
XFS_ILOG_ABROOT = 0x100
XFS_ILOG_DOWNER = 0x200
XFS_ILOG_AOWNER = 0x400
XFS_ILOG_TIMESTAMP = 0x4000

XFS_ILI_FLAGS = {
    XFS_ILOG_CORE      : "CORE",
    XFS_ILOG_DDATA     : "DDATA",
    XFS_ILOG_DEXT      : "DEXT",
    XFS_ILOG_DBROOT    : "DBROOT",
    XFS_ILOG_DEV       : "DEV",
    XFS_ILOG_UUID      : "UUID",
    XFS_ILOG_ADATA     : "ADATA",
    XFS_ILOG_AEXT      : "AEXT",
    XFS_ILOG_ABROOT    : "ABROOT",
    XFS_ILOG_DOWNER    : "DOWNER",
    XFS_ILOG_AOWNER    : "AOWNER",
    XFS_ILOG_TIMESTAMP : "TIMESTAMP",
}

XFS_DQ_USER = 0x0001   # a user quota
XFS_DQ_PROJ = 0x0002   # project quota
XFS_DQ_GROUP = 0x0004  # a group quota
XFS_DQ_DIRTY = 0x0008  # dquot is dirty
XFS_DQ_FREEING = 0x0010 # dquot is being torn down

XFS_DQ_FLAGS = {
    XFS_DQ_USER    : "USER",
    XFS_DQ_PROJ    : "PROJ",
    XFS_DQ_GROUP   : "GROUP",
    XFS_DQ_DIRTY   : "DIRTY",
    XFS_DQ_FREEING : "FREEING",
}

XFS_MOUNT_WSYNC = (1 << 0)
XFS_MOUNT_UNMOUNTING = (1 << 1)
XFS_MOUNT_DMAPI = (1 << 2)
XFS_MOUNT_WAS_CLEAN = (1 << 3)
XFS_MOUNT_FS_SHUTDOWN = (1 << 4)
XFS_MOUNT_DISCARD = (1 << 5)
XFS_MOUNT_NOALIGN = (1 << 7)
XFS_MOUNT_ATTR2 = (1 << 8)
XFS_MOUNT_GRPID = (1 << 9)
XFS_MOUNT_NORECOVERY = (1 << 10)
XFS_MOUNT_DFLT_IOSIZE = (1 << 12)
XFS_MOUNT_SMALL_INUMS = (1 << 14)
XFS_MOUNT_32BITINODES = (1 << 15)
XFS_MOUNT_NOUUID = (1 << 16)
XFS_MOUNT_BARRIER = (1 << 17)
XFS_MOUNT_IKEEP = (1 << 18)
XFS_MOUNT_SWALLOC = (1 << 19)
XFS_MOUNT_RDONLY = (1 << 20)
XFS_MOUNT_DIRSYNC = (1 << 21)
XFS_MOUNT_COMPAT_IOSIZE = (1 << 22)
XFS_MOUNT_FILESTREAMS = (1 << 24)
XFS_MOUNT_NOATTR2 = (1 << 25)

XFS_MOUNT_FLAGS = {
    XFS_MOUNT_WSYNC         : "WSYNC",
    XFS_MOUNT_UNMOUNTING    : "UNMOUNTING",
    XFS_MOUNT_DMAPI         : "DMAPI",
    XFS_MOUNT_WAS_CLEAN     : "WAS_CLEAN",
    XFS_MOUNT_FS_SHUTDOWN   : "FS_SHUTDOWN",
    XFS_MOUNT_DISCARD       : "DISCARD",
    XFS_MOUNT_NOALIGN       : "NOALIGN",
    XFS_MOUNT_ATTR2         : "ATTR2",
    XFS_MOUNT_GRPID         : "GRPID",
    XFS_MOUNT_NORECOVERY    : "NORECOVERY",
    XFS_MOUNT_DFLT_IOSIZE   : "DFLT_IOSIZE",
    XFS_MOUNT_SMALL_INUMS   : "SMALL_INUMS",
    XFS_MOUNT_32BITINODES   : "32BITINODES",
    XFS_MOUNT_NOUUID        : "NOUUID",
    XFS_MOUNT_BARRIER       : "BARRIER",
    XFS_MOUNT_IKEEP         : "IKEEP",
    XFS_MOUNT_SWALLOC       : "SWALLOC",
    XFS_MOUNT_RDONLY        : "RDONLY",
    XFS_MOUNT_DIRSYNC       : "DIRSYNC",
    XFS_MOUNT_COMPAT_IOSIZE : "COMPAT_IOSIZE",
    XFS_MOUNT_FILESTREAMS   : "FILESTREAMS",
    XFS_MOUNT_NOATTR2       : "NOATTR2",
}

class XFSBufDecoder(Decoder):
    """
    Decodes a struct xfs_buf into human-readable form
    """

    def __init__(self, xfsbuf: gdb.Value) -> None:
        super(XFSBufDecoder, self).__init__()
        self.xfsbuf = xfsbuf

    def __str__(self) -> str:
        return xfs_format_xfsbuf(self.xfsbuf)

class XFSBufBioDecoder(Decoder):
    """
    Decodes a bio with an xfsbuf ->bi_end_io

    Args:
        bio: The struct bio to decode.  The value must be of type
            ``struct bio``.

    Attributes:
        xfsbuf (gdb.Value): The xfsbuf structure.  It is of type
            ``struct xfs_buf *``.
        devname (str): The string representation of the device name
    """
    _description = "{:x} bio: xfs buffer on {}"
    __endio__ = 'xfs_buf_bio_end_io'
    _types = Types(['struct xfs_buf *'])

    def __init__(self, bio: gdb.Value) -> None:
        super(XFSBufBioDecoder, self).__init__()
        self.bio = bio

    def interpret(self) -> None:
        """Interpret the xfsbuf bio to populate its attributes"""
        # pylint: disable=attribute-defined-outside-init
        self.xfsbuf = self.bio['bi_private'].cast(self._types.xfs_buf_p_type)
        self.devname = block_device_name(self.bio['bi_bdev'])

    def __next__(self) -> Any:
        return XFSBufDecoder(self.xfsbuf)

    def __str__(self) -> str:
        return self._description.format(self.bio, self.devname)

XFSBufBioDecoder.register()

types = Types(['struct xfs_log_item', 'struct xfs_buf_log_item',
               'struct xfs_inode_log_item', 'struct xfs_efi_log_item',
               'struct xfs_efd_log_item', 'struct xfs_dq_logitem',
               'struct xfs_qoff_logitem', 'struct xfs_inode',
               'struct xfs_mount *', 'struct xfs_buf *'])

class XFS:
    """
    XFS File system state class.  Not meant to be instantiated directly.
    """
    _ail_head_name = None

    @classmethod
    def detect_ail_version(cls, gdbtype: gdb.Type) -> None:
        """
        Detect what version of the ail structure is in use

        Linux v4.17 renamed the xfs_ail members to use
        ail_* instead of xa_* except for xa_ail which
        was renamed to ail_head.

        Meant to be used as a TypeCallback.

        Args:
            gdbtype: The ``struct xfs_ail`` type.
        """
        if struct_has_member(gdbtype, 'ail_head'):
            cls._ail_head_name = 'ail_head'
        else:
            cls._ail_head_name = 'xa_ail'

    @classmethod
    def get_ail_head(cls, ail: gdb.Value) -> gdb.Value:
        return ail[cls._ail_head_name]

def is_xfs_super(super_block: gdb.Value) -> bool:
    """
    Tests whether a ``struct super_block`` belongs to XFS.

    Args:
        super_block: The struct super_block to test. The value must be of type
            ``struct super_block``.

    Returns:
        :obj:`bool`: Whether the super_block belongs to XFS

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return is_fstype_super(super_block, "xfs")

def is_xfs_inode(vfs_inode: gdb.Value) -> bool:
    """
    Tests whether a generic ``struct inode`` belongs to XFS

    Args:
        vfs_inode: The struct inode to test whether it belongs to XFS.
            The value must be of type ``struct inode``.

    Returns:
        :obj:`bool`: Whether the inode belongs to XFS

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """

    return is_fstype_inode(vfs_inode, "xfs")

def xfs_inode(vfs_inode: gdb.Value, force: bool = False) -> gdb.Value:
    """
    Converts a VFS inode to a xfs inode

    This method converts a ``struct inode`` to a ``struct xfs_inode``.

    Args:
        vfs_inode: The ``struct inode`` to convert to a ``struct xfs_inode``
            The value must be of type ``struct inode``.

        force: ignore type checking

    Returns:
        :obj:`gdb.Value`: The converted ``struct xfs_inode``.  The value
        will be of type ``struct xfs_inode``.

    Raises:
        TypeError: The inode does not belong to xfs
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if not force and not is_xfs_inode(vfs_inode):
        raise InvalidArgumentError("inode does not belong to xfs")

    return container_of(vfs_inode, types.xfs_inode, 'i_vnode')

def xfs_mount(sb: gdb.Value, force: bool = False) -> gdb.Value:
    """
    Converts a VFS superblock to a xfs mount

    This method converts a ``struct super_block`` to a ``struct xfs_mount *``

    Args:
        super_block: The struct super_block to convert to a
            ``struct xfs_fs_info``.  The value must be of type
            ``struct super_block``.

    Returns:
        :obj:`gdb.Value`: The converted ``struct xfs_mount``.  The value will be
        of type ``struct xfs_mount *``.

    Raises:
        InvalidArgumentError: The ``struct super_block`` does not belong to xfs
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if not force and not is_xfs_super(sb):
        raise InvalidArgumentError("superblock does not belong to xfs")

    return sb['s_fs_info'].cast(types.xfs_mount_p_type)

def xfs_mount_flags(mp: gdb.Value) -> str:
    """
    Return the XFS-internal mount flags in string form

    Args:
        mp: The ``struct xfs_mount`` for the file system.  The value must be of
            type ``struct xfs_mount``.

    Returns:
        :obj:`str`: The mount flags in string form

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return decode_flags(mp['m_flags'], XFS_MOUNT_FLAGS)

def xfs_mount_uuid(mp: gdb.Value) -> uuid.UUID:
    """
    Return the UUID for an XFS file system in string form

    Args:
        mp: The ``struct xfs_mount`` for the file system.  The value must be of
            type ``struct xfs_mount``.

    Returns:
        :obj:`uuid.UUID`: The Python UUID object that describes the xfs UUID

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    return decode_uuid_t(mp['m_sb']['sb_uuid'])

def xfs_mount_version(mp: gdb.Value) -> int:
    return int(mp['m_sb']['sb_versionnum']) & 0xf

def xfs_for_each_ail_entry(ail: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterates over the XFS Active Item Log and returns each item

    Args:
        ail: The XFS AIL to iterate.  The value must be of type
            ``struct xfs_ail``.

    Yields:
        :obj:`gdb.Value`: A log item from the AIL.  Each value will be of
        type ``struct xfs_log_item``.

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    head = XFS.get_ail_head(ail)
    for item in list_for_each_entry(head, types.xfs_log_item_type, 'li_ail'):
        yield item

def xfs_for_each_ail_log_item(mp: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterates over the XFS Active Item Log and returns each item

    Args:
        mp: The XFS mount to iterate.  The value must be of type `struct
            xfs_mount`.

    Yields:
        :obj:`gdb.Value`: A log item from AIL owned by this mount.
        The value will be of type ``struct xfs_log_item``.

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    for item in xfs_for_each_ail_entry(mp['m_ail']):
        yield item

def item_to_buf_log_item(item: gdb.Value) -> gdb.Value:
    """
    Converts an xfs_log_item to an xfs_buf_log_item

    Args:
        item: The log item to convert.  The value must be of
            type ``struct xfs_log_item``.

    Returns:
        :obj:`gdb.Value`: The converted log item.  The value will be of
        type ``struct xfs_buf_log_item``.

    Raises:
        InvalidArgumentError: The type of log item is not ``XFS_LI_BUF``
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if item['li_type'] != XFS_LI_BUF:
        raise InvalidArgumentError("item is not a buf log item")
    return container_of(item, types.xfs_buf_log_item_type, 'bli_item')

def item_to_inode_log_item(item: gdb.Value) -> gdb.Value:
    """
    Converts an xfs_log_item to an xfs_inode_log_item

    Args:
        item: The log item to convert.  The value must of of type
            ``struct xfs_log_item``.

    Returns:
        :obj:`gdb.Value`: The converted log item.  The value will be of
        type ``struct xfs_inode_log_item``.

    Raises:
        InvalidArgumentError: The type of log item is not ``XFS_LI_INODE``
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if item['li_type'] != XFS_LI_INODE:
        raise InvalidArgumentError("item is not an inode log item")
    return container_of(item, types.xfs_inode_log_item_type, 'ili_item')

def item_to_efi_log_item(item: gdb.Value) -> gdb.Value:
    """
    Converts an xfs_log_item to an xfs_efi_log_item

    Args:
        item: The log item to convert.  The value must of of type
            ``struct xfs_log_item``.

    Returns:
        :obj:`gdb.Value`: The converted log item.  The value will be of
        type ``struct xfs_efi_log_item``.

    Raises:
        InvalidArgumentError: The type of log item is not ``XFS_LI_EFI``
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if item['li_type'] != XFS_LI_EFI:
        raise InvalidArgumentError("item is not an EFI log item")
    return container_of(item, types.xfs_efi_log_item_type, 'efi_item')

def item_to_efd_log_item(item: gdb.Value) -> gdb.Value:
    """
    Converts an xfs_log_item to an xfs_efd_log_item

    Args:
        item: The log item to convert.  The value must of of type
        ``struct xfs_log_item``.

    Returns:
        :obj:`gdb.Value`: The converted log item.  The value will be of
        type ``struct xfs_efd_log_item``.

    Raises:
        InvalidArgumentError: The type of log item is not ``XFS_LI_EFD``
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if item['li_type'] != XFS_LI_EFD:
        raise InvalidArgumentError("item is not an EFD log item")
    return container_of(item, types.xfs_efd_log_item_type, 'efd_item')

def item_to_dquot_log_item(item: gdb.Value) -> gdb.Value:
    """
    Converts an xfs_log_item to an xfs_dquot_log_item

    Args:
        item: The log item to convert.  The value must of of type
            ``struct xfs_log_item``.

    Returns:
        :obj:`gdb.Value`: The converted log item.  The value will be of
        type ``struct xfs_dquot_log_item``.

    Raises:
        InvalidArgumentError: The type of log item is not ``XFS_LI_DQUOT``
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if item['li_type'] != XFS_LI_DQUOT:
        raise InvalidArgumentError("item is not an DQUOT log item")
    return container_of(item, types.xfs_dq_logitem_type, 'qli_item')

def item_to_quotaoff_log_item(item: gdb.Value) -> gdb.Value:
    """
    Converts an xfs_log_item to an xfs_quotaoff_log_item

    Args:
        item: The log item to convert.  The value must be of type
            ``struct xfs_log_item``.

    Returns:
        :obj:`gdb.Value`: The converted log item.  The value will be of
        type ``struct xfs_quotaoff_log_item``

    Raises:
        InvalidArgumentError: The type of log item is not ``XFS_LI_QUOTAOFF``
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if item['li_type'] != XFS_LI_QUOTAOFF:
        raise InvalidArgumentError("item is not an QUOTAOFF log item")
    return container_of(item, types.xfs_qoff_logitem_type, 'qql_item')

def xfs_log_item_typed(item: gdb.Value) -> gdb.Value:
    """
    Returns the log item converted from the generic type to the actual type

    Args:
        item: The ``struct xfs_log_item`` to convert.  The value must be
            of type ``struct xfs_log_item``.

    Returns:
        :obj:`gdb.Value`:

        Depending on type, the value will be any of the following types:

            - ``struct xfs_buf_log_item_type``
            - ``struct xfs_inode_log_item_type``
            - ``struct xfs_efi_log_item_type``
            - ``struct xfs_efd_log_item_type``
            - ``struct xfs_dq_logitem``
            - ``int`` (for ``XFS_LI_IUNLINK`` item)

    Raises:
        RuntimeError: An unexpected item type was encountered
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    li_type = int(item['li_type'])
    if li_type == XFS_LI_BUF:
        typed_item = item_to_buf_log_item(item)
    elif li_type == XFS_LI_INODE:
        typed_item = item_to_inode_log_item(item)
    elif li_type == XFS_LI_EFI:
        typed_item = item_to_efi_log_item(item)
    elif li_type == XFS_LI_EFD:
        typed_item = item_to_efd_log_item(item)
    elif li_type == XFS_LI_IUNLINK:
        # There isn't actually any type information for this
        typed_item = item['li_type']
    elif li_type == XFS_LI_DQUOT:
        typed_item = item_to_dquot_log_item(item)
    elif li_type == XFS_LI_QUOTAOFF:
        typed_item = item_to_quotaoff_log_item(item)
    else:
        raise RuntimeError("Unknown AIL item type {:x}".format(li_type))
    return typed_item

def xfs_format_xfsbuf(buf: gdb.Value) -> str:
    """
    Returns a human-readable format of ``struct xfs_buf``

    Args:
        buf: The ``struct xfs_buf`` to decode.  The value must be of type
            ``struct xfs_buf``.

    Returns:
        :obj:`str`: The human-readable representation of the
            ``struct xfs_buf``.

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    state = ""
    bflags = decode_flags(buf['b_flags'], XFS_BUF_FLAGS)

    if buf['b_pin_count']['counter']:
        state += "P"
    if buf['b_sema']['count'] >= 0:
        state += "L"

    return f"{int(buf):x} xfsbuf: logical offset {buf['b_bn']:d}, " \
           f"size {buf['b_buffer_len']:d}, block number {buf['b_bn']:d}, " \
           f"flags {bflags}, state {state}"

def xfs_for_each_ail_log_item_typed(mp: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterates over the XFS Active Item Log and returns each item, resolved
    to the specific type.

    Args:
        mp: The XFS mount to iterate.  The value must be of
            type ``struct xfs_mount``.

    Yields:
        :obj:`gdb.Value`:

        Depending on type, the value will be any of the following types:

        - ``struct xfs_buf_log_item_type``
        - ``struct xfs_inode_log_item_type``
        - ``struct xfs_efi_log_item_type``
        - ``struct xfs_efd_log_item_type``
        - ``struct xfs_dq_logitem``
        - ``int`` (for UNLINK item)

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    for item in types.xfs_for_each_ail_log_item(mp):
        yield types.xfs_log_item_typed(item)

type_cbs = TypeCallbacks([('struct xfs_ail', XFS.detect_ail_version)])
