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
        return list_for_each_entry(task['nsproxy']['mnt_ns']['list'],
                                   types.mount_type, 'mnt_list')

    @classmethod
    def check_task_interface(cls, symval):
        try:
            nsproxy = symvals.init_task['nsproxy']
            cls.for_each_mount_impl = cls.for_each_mount_nsproxy
        except KeyError:
            print("check_task_interface called but no init_task?")
            pass

def check_mount_type(gdbtype):
    try:
        types.mount_type = gdb.lookup_type('struct mount')
    except gdb.error:
        # Older kernels didn't separate mount from vfsmount
        types.mount_type = types.vfsmount_type

def for_each_mount(task=None):
    if task is None:
        task = symvals.init_task
    return Mount.for_each_mount_impl(task)

def real_mount(vfsmnt):
    if (vfsmnt.type == types.mount_type or
        vfsmnt.type == types.mount_type.pointer()):
        t = vfsmnt.type
        if t.code == gdb.TYPE_CODE_PTR:
            t = t.target()
        if t is not types.mount_type:
            types.mount_type = t
        return vfsmnt
    return container_of(vfsmnt, types.mount_type, 'mnt')

def mount_flags(mnt, show_hidden=False):
    if struct_has_member(mnt, 'mnt'):
        mnt = mnt['mnt']
    if show_hidden:
        return decode_flags(mnt['mnt_flags'], MNT_FLAGS_HIDDEN, ",")
    return decode_flags(mnt['mnt_flags'], MNT_FLAGS, ",")

def mount_super(mnt):
    try:
        sb = mnt['mnt']['mnt_sb']
    except gdb.error:
        sb = mnt['mnt_sb']
    return sb

def mount_root(mnt):
    try:
        mnt = mnt['mnt']
    except gdb.error:
        pass

    return mnt['mnt_root']

def mount_fstype(mnt):
    return super_fstype(mount_super(mnt))

def mount_device(mnt):
    devname = mnt['mnt_devname'].string()
    if devname is None:
        devname = "none"
    return devname

def d_path(mnt, dentry, root=None):
    if root is None:
        root = symvals.init_task['fs']['root']

    if dentry.type.code != gdb.TYPE_CODE_PTR:
        dentry = dentry.address

    if mnt.type.code != gdb.TYPE_CODE_PTR:
        mnt = mnt.address

    mount = real_mount(mnt)
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

type_cbs = TypeCallbacks([ ('struct vfsmount', check_mount_type ) ])
symbols_cbs = SymbolCallbacks([ ('init_task', Mount.check_task_interface ) ])
