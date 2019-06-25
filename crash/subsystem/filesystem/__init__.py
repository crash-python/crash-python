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

S_IFMT = 0o170000
S_IFSOCK = 0o140000
S_IFLNK = 0o120000
S_IFREG = 0o100000
S_IFBLK = 0o060000
S_IFDIR = 0o040000
S_IFCHR = 0o020000
S_IFIFO = 0o010000

S_ISUID = 0o0004000
S_ISGID = 0o0002000
S_ISVTX = 0o0001000

S_IRWXU = 0o00700
S_IRUSR = 0o00400
S_IWUSR = 0o00200
S_IXUSR = 0o00100

S_IRWXG = 0o00070
S_IRGRP = 0o00040
S_IWGRP = 0o00020
S_IXGRP = 0o00010

S_IRWXO = 0o00007
S_IROTH = 0o00004
S_IWOTH = 0o00002
S_IXOTH = 0o00001

INODE_MODE_BITS = {
    S_IFSOCK : 'S_IFSOCK',
    S_IFLNK : 'S_IFLNK',
    S_IFREG : 'S_IFREG',
    S_IFBLK : 'S_IFBLK',
    S_IFDIR : 'S_IFDIR',
    S_IFCHR : 'S_IFCHR',
    S_IFIFO : 'S_IFIFO',
    S_ISUID : 'S_ISUID',
    S_ISGID : 'S_ISGID',
    S_ISVTX : 'S_ISVTX',
    S_IRWXU : 'S_IRWXU',
    S_IRUSR : 'S_IRUSR',
    S_IWUSR : 'S_IWUSR',
    S_IXUSR : 'S_IXUSR',
    S_IRWXG : 'S_IRWXG',
    S_IRGRP : 'S_IRGRP',
    S_IWGRP : 'S_IWGRP',
    S_IXGRP : 'S_IXGRP',
    S_IRWXO : 'S_IRWXO',
    S_IROTH : 'S_IROTH',
    S_IWOTH : 'S_IWOTH',
    S_IXOTH : 'S_IXOTH',
}

_inode_fmt_bits = {
    S_IFSOCK : 's',
    S_IFLNK : 'l',
    S_IFREG : '-',
    S_IFBLK : 'b',
    S_IFDIR : 'd',
    S_IFCHR : 'c',
    S_IFIFO : 'p',
}

_inode_rwx_bits = {
    S_IRUSR : 'r',
    S_IWUSR : 'w',
    S_IXUSR : 'x',
    S_IRGRP : 'r',
    S_IWGRP : 'w',
    S_IXGRP : 'x',
    S_IROTH : 'r',
    S_IWOTH : 'w',
    S_IXOTH : 'x',
}

def ls_style_mode_perms(i_mode: gdb.Value) -> str:
    mode = int(i_mode)

    fmt = '?'
    for bit in sorted(_inode_fmt_bits.keys()):
        if (bit & i_mode) == bit:
            fmt = _inode_fmt_bits[bit]

    perms = [fmt]

    for bit in sorted(_inode_rwx_bits.keys(), reverse=True):
        if (bit & i_mode) == bit:
            perms.append(_inode_rwx_bits[bit])
        else:
            perms.append('-')

    if mode & S_ISUID:
        if mode & S_IXUSR:
            perms[3] = 's'
        else:
            perms[3] = 'S'

    if mode & S_ISGID:
        if mode & S_IXGRP:
            perms[6] = 's'
        else:
            perms[6] = 'S'

    if mode & S_ISVTX:
        if mode & S_IXOTH:
            perms[9] = 't'
        else:
            perms[9] = 'T'

    return "".join(perms)

def ls_style_inode_perms(inode: gdb.Value) -> str:
    return ls_style_mode_perms(inode['i_mode'])

def _S_ISMODE(i_mode: int, mode: int) -> bool:
    return (i_mode & S_IFMT) == mode

def S_ISLNK(i_mode: int) -> bool:
    return _S_ISMODE(i_mode, S_IFLNK)

def S_ISREG(i_mode: int) -> bool:
    return _S_ISMODE(i_mode, S_IFREG)

def S_ISDIR(i_mode: int) -> bool:
    return _S_ISMODE(i_mode, S_IFDIR)

def S_ISCHR(i_mode: int) -> bool:
    return _S_ISMODE(i_mode, S_IFCHR)

def S_ISBLK(i_mode: int) -> bool:
    return _S_ISMODE(i_mode, S_IFBLK)

def S_ISFIFO(i_mode: int) -> bool:
    return _S_ISMODE(i_mode, S_IFIFO)

def S_ISSOCK(i_mode: int) -> bool:
    return _S_ISMODE(i_mode, S_IFSOCK)

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
            x = int(sb['s_dev']) # pylint: disable=unused-variable
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
