# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.infra import CrashBaseClass, export
from crash.subsystem.filesystem import super_fstype
from crash.types.list import list_for_each_entry
from crash.util import container_of, decode_flags, struct_has_member

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


class Mount(CrashBaseClass):
    __types__ = [ 'struct mount', 'struct vfsmount' ]
    __symvals__ = [ 'init_task' ]
    __type_callbacks__ = [ ('struct vfsmount', 'check_mount_type' ) ]
    __symbol_callbacks__ = [ ('init_task', 'check_task_interface' ) ]

    @classmethod
    def for_each_mount_impl(cls, task):
        raise NotImplementedError("Mount.for_each_mount is unhandled on this kernel version.")

    @classmethod
    def check_mount_type(cls, gdbtype):
        try:
            cls.mount_type = gdb.lookup_type('struct mount')
        except gdb.error:
            # Older kernels didn't separate mount from vfsmount
            cls.mount_type = cls.vfsmount_type

    @classmethod
    def check_task_interface(cls, symval):
        try:
            nsproxy = cls.init_task['nsproxy']
            cls.for_each_mount_impl = cls.for_each_mount_nsproxy
        except KeyError:
            print("check_task_interface called but no init_task?")
            pass

    @export
    def for_each_mount(self, task=None):
        if task is None:
            task = self.init_task
        return self.for_each_mount_impl(task)

    def for_each_mount_nsproxy(self, task):
        return list_for_each_entry(task['nsproxy']['mnt_ns']['list'],
                                   self.mount_type, 'mnt_list')

    @export
    @classmethod
    def real_mount(cls, vfsmnt):
        if (vfsmnt.type == cls.mount_type or
            vfsmnt.type == cls.mount_type.pointer()):
            t = vfsmnt.type
            if t.code == gdb.TYPE_CODE_PTR:
                t = t.target()
            if t is not cls.mount_type:
                cls.mount_type = t
            return vfsmnt
        return container_of(vfsmnt, cls.mount_type, 'mnt')

    @export
    @classmethod
    def mount_flags(cls, mnt, show_hidden=False):
        if struct_has_member(mnt, 'mnt'):
            mnt = mnt['mnt']
        if show_hidden:
            return decode_flags(mnt['mnt_flags'], MNT_FLAGS_HIDDEN, ",")
        return decode_flags(mnt['mnt_flags'], MNT_FLAGS, ",")

    @export
    @staticmethod
    def mount_super(mnt):
        try:
            sb = mnt['mnt']['mnt_sb']
        except gdb.error:
            sb = mnt['mnt_sb']
        return sb

    @export
    @staticmethod
    def mount_root(mnt):
        try:
            mnt = mnt['mnt']
        except gdb.error:
            pass

        return mnt['mnt_root']

    @export
    @classmethod
    def mount_fstype(cls, mnt):
        return super_fstype(cls.mount_super(mnt))

    @export
    @classmethod
    def mount_device(cls, mnt):
        devname = mnt['mnt_devname'].string()
        if devname is None:
            devname = "none"
        return devname

    @export
    @classmethod
    def d_path(cls, mnt, dentry, root=None):
        if root is None:
            root = cls.init_task['fs']['root']

        if dentry.type.code != gdb.TYPE_CODE_PTR:
            dentry = dentry.address

        if mnt.type.code != gdb.TYPE_CODE_PTR:
            mnt = mnt.address

        mount = cls.real_mount(mnt)
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
