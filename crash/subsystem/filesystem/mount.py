# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.subsystem.filesystem import super_fstype
from crash.types.list import list_for_each_entry
from crash.util import container_of, decode_flags, struct_has_member
from crash.util.symbols import Types, Symvals, TypeCallbacks, SymbolCallbacks

MNT_NOSUID      = 0x01
MNT_NODEV       = 0x02
MNT_NOEXEC      = 0x04
MNT_NOATIME     = 0x08
MNT_NODIRATIME  = 0x10
MNT_RELATIME    = 0x20
MNT_READONLY    = 0x40
MNT_SHRINKABLE  = 0x100
MNT_WRITE_HOLD  = 0x200
MNT_SHARED      = 0x1000
MNT_UNBINDABLE  = 0x2000

MNT_FLAGS = {
    MNT_NOSUID      : "MNT_NOSUID",
    MNT_NODEV       : "MNT_NODEV",
    MNT_NOEXEC      : "MNT_NOEXEC",
    MNT_NOATIME     : "MNT_NOATIME",
    MNT_NODIRATIME  : "MNT_NODIRATIME",
    MNT_RELATIME    : "MNT_RELATIME",
    MNT_READONLY    : "MNT_READONLY",
}

MNT_FLAGS_HIDDEN = {
    MNT_SHRINKABLE : "[MNT_SHRINKABLE]",
    MNT_WRITE_HOLD : "[MNT_WRITE_HOLD]",
    MNT_SHARED : "[MNT_SHARED]",
    MNT_UNBINDABLE : "[MNT_UNBINDABLE]",
}
MNT_FLAGS_HIDDEN.update(MNT_FLAGS)

types = Types([ 'struct mount', 'struct vfsmount' ])
symvals = Symvals([ 'init_task' ])

class Mount(object):
    @classmethod
    def for_each_mount_impl(cls, task):
        raise NotImplementedError("Mount.for_each_mount is unhandled on this kernel version.")

    @classmethod
    def for_each_mount_nsproxy(cls, task):
        """
        An implementation of for_each_mount that uses the task's
        nsproxy to locate the mount namespace.  See for_each_mount
        for more details.
        """
        return list_for_each_entry(task['nsproxy']['mnt_ns']['list'],
                                   types.mount_type, 'mnt_list')

    @classmethod
    def _check_task_interface(cls, symval):
        try:
            nsproxy = symvals.init_task['nsproxy']
            cls.for_each_mount_impl = cls.for_each_mount_nsproxy
        except KeyError:
            print("check_task_interface called but no init_task?")
            pass

def _check_mount_type(gdbtype):
    try:
        types.mount_type = gdb.lookup_type('struct mount')
    except gdb.error:
        # Older kernels didn't separate mount from vfsmount
        types.mount_type = types.vfsmount_type

def for_each_mount(task=None):
    """
    Iterate over each mountpoint in the namespace of the specified task

    If no task is given, the init_task is used.

    The type of the mount structure returned depends on whether
    'struct mount' exists on the kernel version being debugged.

    Args:
        task (gdb.Value<struct task_struct>, default=<symbol:init_task>):
            The task which contains the namespace to iterate.

    Yields:
        gdb.Value<struct vfsmount or struct mount>:
            A mountpoint attached to the namespace.

    """
    if task is None:
        task = symvals.init_task
    return Mount.for_each_mount_impl(task)

def mount_flags(mnt: gdb.Value, show_hidden: bool=False) -> str:
    """
    Returns the human-readable flags of the mount structure

    Args:
        mnt (gdb.Value<struct vfsmount or struct mount>):
            The mount structure for which to return flags

        show_hidden (bool, default=False):
            Whether to return hidden flags

    Returns:
        str: The mount flags in human-readable form
    """
    if struct_has_member(mnt, 'mnt'):
        mnt = mnt['mnt']
    if show_hidden:
        return decode_flags(mnt['mnt_flags'], MNT_FLAGS_HIDDEN, ",")
    return decode_flags(mnt['mnt_flags'], MNT_FLAGS, ",")

def mount_super(mnt: gdb.Value) -> gdb.Value:
    """
    Returns the struct super_block associated with a mount

    Args:
        mnt: gdb.Value<struct vfsmount or struct mount>:
            The mount structure for which to return the super_block

    Returns:
        gdb.Value<struct super_block>:
            The super_block associated with the mount
    """
    try:
        sb = mnt['mnt']['mnt_sb']
    except gdb.error:
        sb = mnt['mnt_sb']
    return sb

def mount_root(mnt: gdb.Value) -> gdb.Value:
    """
    Returns the struct dentry corresponding to the root of a mount

    Args:
        mnt: gdb.Value<struct vfsmount or struct mount>:
            The mount structure for which to return the root dentry

    Returns:
        gdb.Value<struct dentry>:
            The dentry that corresponds to the root of the mount
    """
    try:
        mnt = mnt['mnt']
    except gdb.error:
        pass

    return mnt['mnt_root']

def mount_fstype(mnt: gdb.Value) -> str:
    """
    Returns the file system type of the mount

    Args:
        mnt (gdb.Value<struct vfsmount or struct mount>):
            The mount structure for which to return the file system tyoe

    Returns:
        str: The file system type of the mount in string form
    """
    return super_fstype(mount_super(mnt))

def mount_device(mnt: gdb.Value) -> str:
    """
    Returns the device name that this mount is using

    Args:
        gdb.Value<struct vfsmount or mount>:
            The mount structure for which to get the device name

    Returns:
        str: The device name in string form

    """
    devname = mnt['mnt_devname'].string()
    if devname is None:
        devname = "none"
    return devname

def _real_mount(vfsmnt):
    if (vfsmnt.type == types.mount_type or
        vfsmnt.type == types.mount_type.pointer()):
        t = vfsmnt.type
        if t.code == gdb.TYPE_CODE_PTR:
            t = t.target()
        if t is not types.mount_type:
            types.mount_type = t
        return vfsmnt
    return container_of(vfsmnt, types.mount_type, 'mnt')

def d_path(mnt, dentry, root=None):
    """
    Returns a file system path described by a mount and dentry

    Args:
        mnt (gdb.Value<struct vfsmount or struct mount>):
            The mount for the start of the path

        dentry (gdb.Value<struct dentry>):
            The dentry for the start of the path

        root (gdb.Value<struct vfsmount or struct mount>, default=None):
            The mount at which to stop resolution.  If None,
            the current root of the namespace.

    Returns:
        str: The path in string form
    """
    if root is None:
        root = symvals.init_task['fs']['root']

    if dentry.type.code != gdb.TYPE_CODE_PTR:
        dentry = dentry.address

    if mnt.type.code != gdb.TYPE_CODE_PTR:
        mnt = mnt.address

    mount = _real_mount(mnt)
    if mount.type.code != gdb.TYPE_CODE_PTR:
        mount = mount.address

    try:
        mnt = mnt['mnt'].address
    except gdb.error:
        pass

    name = ""

    # Gone are the days where finding the root was as simple as
    # dentry == dentry->d_parent
    while dentry != root['dentry'] or mnt != root['mnt']:
        if dentry == mnt['mnt_root'] or dentry == dentry['d_parent']:
            if dentry != mnt['mnt_root']:
                return None
            if mount != mount['mnt_parent']:
                dentry = mount['mnt_mountpoint']
                mount = mount['mnt_parent']
                try:
                    mnt = mount['mnt'].address
                except gdb.error:
                    mnt = mount
                continue
            break

        name = "/" + dentry['d_name']['name'].string() + name
        dentry = dentry['d_parent']
    if not name:
        name = '/'
    return name

type_cbs = TypeCallbacks([ ('struct vfsmount', _check_mount_type ) ])
symbols_cbs = SymbolCallbacks([ ('init_task', Mount._check_task_interface ) ])
