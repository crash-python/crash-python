# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
The crash.subsystem.filesystem.mount module contains helpers used to
access the file system namespace.

.. _mount_structure:

*NOTE*: Linux v3.3 split ``struct mount`` from ``struct vfsmount``.  Prior
kernels do not have ``struct mount``.  In functions documented as using a
:obj:`gdb.Value` describing a ``struct mount``, a ``struct vfsmount``
will be required and/or returned instead.
"""

from typing import Iterator, Callable, Any

from crash.subsystem.filesystem import super_fstype
from crash.types.list import list_for_each_entry
from crash.util import container_of, decode_flags, struct_has_member
from crash.util.symbols import Types, Symvals, TypeCallbacks, SymbolCallbacks

import gdb

MNT_NOSUID = 0x01
MNT_NODEV = 0x02
MNT_NOEXEC = 0x04
MNT_NOATIME = 0x08
MNT_NODIRATIME = 0x10
MNT_RELATIME = 0x20
MNT_READONLY = 0x40
MNT_SHRINKABLE = 0x100
MNT_WRITE_HOLD = 0x200
MNT_SHARED = 0x1000
MNT_UNBINDABLE = 0x2000

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

types = Types(['struct mount', 'struct vfsmount'])
symvals = Symvals(['init_task'])

class Mount:
    _for_each_mount: Callable[[Any, gdb.Value], Iterator[gdb.Value]]
    _init_fs_root: gdb.Value

    def _for_each_mount_nsproxy(self, task: gdb.Value) -> Iterator[gdb.Value]:
        """
        An implementation of for_each_mount that uses the task's
        nsproxy to locate the mount namespace.  See :ref:`for_each_mount`
        for more details.
        """
        return list_for_each_entry(task['nsproxy']['mnt_ns']['list'],
                                   types.mount_type, 'mnt_list')

    @classmethod
    def check_task_interface(cls, init_task: gdb.Symbol) -> None:
        """
        Check which interface to iterating over mount structures is in use

        Meant to be used as a SymbolCallback.

        Args:
            init_task: The ``init_task`` symbol.
        """
        cls._init_fs_root = init_task.value()['fs']['root']
        if struct_has_member(init_task, 'nsproxy'):
            cls._for_each_mount = cls._for_each_mount_nsproxy
        else:
            raise NotImplementedError("Mount.for_each_mount is unhandled on this kernel version")

    def for_each_mount(self, task: gdb.Value) -> Iterator[gdb.Value]:
        return self._for_each_mount(task)

    @property
    def init_fs_root(self) -> gdb.Value:
        return self._init_fs_root

_Mount = Mount()

# pylint: disable=unused-argument
def _check_mount_type(gdbtype: gdb.Type) -> None:
    try:
        types.mount_type = gdb.lookup_type('struct mount') # type: ignore
    except gdb.error:
        # Older kernels didn't separate mount from vfsmount
        types.mount_type = types.vfsmount_type # type: ignore

def for_each_mount(task: gdb.Value = None) -> Iterator[gdb.Value]:
    """
    Iterate over each mountpoint in the namespace of the specified task

    If no task is given, the ``init_task`` symbol is used.

    The type of the mount structure returned depends on whether
    ``struct mount`` exists on the kernel version being debugged :ref:`structure <mount_structure>`.

    Args:
        task: The task which contains the namespace to iterate.  The
            :obj:`gdb.Value` must describe a ``struct task_struct``.  If
            unspecified, the value for the ``init_task`` symbol will be
            used.

    Yields:
        :obj:`gdb.Value`: A mountpoint attached to the namespace.
        The value will be of type ``struct mount``
        :ref:`structure <mount_structure>` .

    Raises:
        :obj:`gdb.NotAvailableError`: The target value is not available.
    """
    if task is None:
        task = symvals.init_task
    return _Mount.for_each_mount(task)

def mount_flags(mnt: gdb.Value, show_hidden: bool = False) -> str:
    """
    Returns the human-readable flags of the ``struct mount``
    :ref:`structure <mount_structure>`.

    Args:
        mnt: The :ref:`mount structure <mount_structure>` for which to
            return flags

        show_hidden: Whether to return hidden flags

    Returns:
        :obj:`str`: The mount flags in human-readable form
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
        mnt: The :ref:`mount structure <mount_structure>` for which to
            return the super_block

    Returns:
        :obj:`gdb.Value`: The super_block associated with the mount.
            The value will be of type ``struct super_block``.
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
        mnt: The :ref:`mount structure <mount_structure>` for which to
            return the root dentry

    Returns:
        :obj:`gdb.Value`: The dentry that corresponds to the root of
            the mount.  The value will be of type ``struct dentry``.
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
        mnt: The :ref:`mount structure <mount_structure>` for which to
            return the file system type

    Returns:
        :obj:`str`: The file system type of the mount in string form
    """
    return super_fstype(mount_super(mnt))

def mount_device(mnt: gdb.Value) -> str:
    """
    Returns the device name that this mount is using

    Args:
        mnt: The :ref:`mount structure <mount_structure>` for which to
            get the device name

    Returns:
        :obj:`str`: The device name in string form

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    devname = mnt['mnt_devname'].string()
    if devname is None:
        devname = "none"
    return devname

def _real_mount(vfsmnt: gdb.Value) -> gdb.Value:
    if (vfsmnt.type == types.mount_type or
            vfsmnt.type == types.mount_type.pointer()):
        t = vfsmnt.type
        if t.code == gdb.TYPE_CODE_PTR:
            t = t.target()
        if t is not types.mount_type:
            types.mount_type = t # type: ignore
        return vfsmnt
    return container_of(vfsmnt, types.mount_type, 'mnt')

def d_path(mnt: gdb.Value, dentry: gdb.Value, root: gdb.Value = None) -> str:
    """
    Returns a file system path described by a mount and dentry

    Args:
        mnt: The :ref:`mount structure <mount_structure>` for the start
            of the path

        dentry: The dentry for the start of the path.  The value must be
            of type ``struct dentry``.
        root: The :ref:`mount structure <mount_structure>` at which to
            stop resolution.  If unspecified or ``None``, the current root
            of the namespace is used.

    Returns:
        :obj:`str`: The path in string form

    Raises:
        :obj:`gdb.NotAvailableError`: The target value was not available.
    """
    if root is None:
        root = _Mount.init_fs_root

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
        # pylint: disable=consider-using-in
        if dentry == mnt['mnt_root'] or dentry == dentry['d_parent']:
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

type_cbs = TypeCallbacks([('struct vfsmount', _check_mount_type)])
symbols_cbs = SymbolCallbacks([('init_task', Mount.check_task_interface)])
