# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from argparse import Namespace
from crash.commands import Command, ArgumentParser
from crash.types.task import LinuxTask
from crash.subsystem.filesystem.mount import MNT_NOSUID, MNT_NODEV, MNT_NOEXEC
from crash.subsystem.filesystem.mount import MNT_NOATIME, MNT_NODIRATIME
from crash.subsystem.filesystem.mount import MNT_RELATIME, MNT_READONLY
from crash.subsystem.filesystem.mount import MNT_SHRINKABLE, MNT_WRITE_HOLD
from crash.subsystem.filesystem.mount import MNT_SHARED, MNT_UNBINDABLE
from crash.subsystem.filesystem.mount import d_path, for_each_mount
from crash.subsystem.filesystem.mount import mount_device, mount_fstype
from crash.subsystem.filesystem.mount import mount_super, mount_flags
from crash.subsystem.filesystem.mount import mount_root

class _Parser(ArgumentParser):
    """
    NAME
      mount - display mounted file systems

      -f    display common mount flags
      -v    display superblock and vfsmount addresses
      -d    display device obtained from super_block
    """

class MountCommand(Command):
    """display mounted file systems"""

    def __init__(self, name):
        parser = _Parser(prog=name)

        parser.add_argument('-v', action='store_true', default=False)
        parser.add_argument('-f', action='store_true', default=False)
        parser.add_argument('-d', action='store_true', default=False)

        super().__init__(name, parser)

    def __getattr__(self, name):
        if name == 'charp':
            self.charp = gdb.lookup_type('char').pointer()
        else:
            raise AttributeError

        return getattr(self, name)

    def execute(self, args):
        if args.v:
            print("{:^16} {:^16} {:^10} {:^16} {}"
                  .format("MOUNT", "SUPERBLK", "TYPE", "DEVNAME", "PATH"))
        for mnt in for_each_mount():
            self.show_one_mount(mnt, args)

    def show_one_mount(self, mnt: gdb.Value, args: Namespace,
                       task: LinuxTask = None) -> None:
        if mnt.type.code == gdb.TYPE_CODE_PTR:
            mnt = mnt.dereference()

        flags = ""
        if args.f:
            flags = " ({})".format(mount_flags(mnt))
        path = d_path(mnt, mount_root(mnt))
        if args.v:
            print("{:016x} {:016x}  {:<10} {:<16} {}"
                  .format(int(mnt.address), int(mount_super(mnt)),
                          mount_fstype(mnt), mount_device(mnt), path))
        else:
            print("{} on {} type {}{}"
                  .format(mount_device(mnt), path, mount_fstype(mnt), flags))

MountCommand("mount")
