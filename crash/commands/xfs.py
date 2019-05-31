# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import os.path
import argparse
import re

from argparse import Namespace
from crash.commands import Command, ArgumentParser
from crash.commands import CommandLineError, CommandError
from crash.exceptions import DelayedAttributeError
from crash.types.list import list_for_each_entry, list_empty
from crash.subsystem.filesystem import for_each_super_block, get_super_block
from crash.subsystem.filesystem import super_flags
from crash.subsystem.filesystem.xfs import xfs_mount
from crash.subsystem.filesystem.xfs import xfs_for_each_ail_log_item
from crash.subsystem.filesystem.xfs import xfs_log_item_typed
from crash.subsystem.filesystem.xfs import xfs_format_xfsbuf
from crash.subsystem.filesystem.xfs import XFS_LI_TYPES
from crash.subsystem.filesystem.xfs import XFS_LI_EFI, XFS_LI_EFD
from crash.subsystem.filesystem.xfs import XFS_LI_IUNLINK, XFS_LI_INODE
from crash.subsystem.filesystem.xfs import XFS_LI_BUF, XFS_LI_DQUOT
from crash.subsystem.filesystem.xfs import XFS_LI_QUOTAOFF, XFS_BLI_FLAGS
from crash.subsystem.filesystem.xfs import XFS_DQ_FLAGS
from crash.subsystem.filesystem.xfs import xfs_mount_flags, xfs_mount_uuid
from crash.subsystem.filesystem.xfs import xfs_mount_version
from crash.util import decode_flags
from crash.util.symbols import Types

types = Types(['struct xfs_buf *'])

class _Parser(ArgumentParser):
    """
    NAME
      xfs - display XFS internal data structures

    SYNOPSIS
      xfs <command> [arguments ...]

    COMMANDS
      xfs list
      xfs show <superblock>
      xfs dump-ail <superblock>
      xfs dump-buft <buftarg>
    """

class XFSCommand(Command):
    """display XFS internal data structures"""

    def __init__(self, name):
        parser = ArgumentParser(prog=name)
        subparsers = parser.add_subparsers(help="sub-command help")
        show_parser = subparsers.add_parser('show', help='show help')
        show_parser.set_defaults(subcommand=self.show_xfs)
        show_parser.add_argument('addr')
        list_parser = subparsers.add_parser('list', help='list help')
        list_parser.set_defaults(subcommand=self.list_xfs)
        ail_parser = subparsers.add_parser('dump-ail', help='ail help')
        ail_parser.set_defaults(subcommand=self.dump_ail)
        ail_parser.add_argument('addr')
        buft_parser = subparsers.add_parser('dump-buft', help='buft help')
        buft_parser.set_defaults(subcommand=self.dump_buftargs)
        buft_parser.add_argument('addr')

        Command.__init__(self, name, parser)

    def list_xfs(self, args: Namespace) -> None:
        count = 0
        print_header = True
        for sb in for_each_super_block():
            if sb['s_type']['name'].string() == "xfs":
                mp = xfs_mount(sb)
                u = xfs_mount_uuid(mp)
                if print_header:
                    print_header = False
                    print("SUPER BLOCK\t\t\tDEVICE\t\tUUID")

                print("{}\t{}\t{}".format(sb.address, sb['s_id'].string(), u))
                count += 1

        if count == 0:
            print("No xfs file systems are mounted.")

    def show_xfs(self, args: Namespace) -> None:
        try:
            sb = get_super_block(args.addr)
        except gdb.NotAvailableError as e:
            raise CommandError(str(e))

        mp = xfs_mount(sb)

        print("Device: {}".format(sb['s_id'].string()))
        print("UUID: {}".format(xfs_mount_uuid(mp)))
        print("VFS superblock flags: {}".format(super_flags(sb)))
        print("Flags: {}".format(xfs_mount_flags(mp)))
        print("Version: {}".format(xfs_mount_version(mp)))
        if list_empty(mp['m_ail']['xa_ail']):
            print("AIL is empty")
        else:
            print("AIL has items queued")

    def dump_ail(self, args: Namespace) -> None:
        try:
            sb = get_super_block(args.addr)
        except gdb.NotAvailableError as e:
            raise CommandError(str(e))

        mp = xfs_mount(sb)
        ail = mp['m_ail']
        itemno = 0
        print("AIL @ {:x}".format(int(ail)))
        print("target={} last_pushed_lsn={} log_flush="
              .format(int(ail['xa_target']), int(ail['xa_last_pushed_lsn'])),
              end='')
        try:
            print("{}".format(int(ail['xa_log_flush'])))
        except:
            print("[N/A]")

        for bitem in xfs_for_each_ail_log_item(mp):
            li_type = int(bitem['li_type'])
            lsn = int(bitem['li_lsn'])
            item = xfs_log_item_typed(bitem)
            print("{}: item={:x} lsn={} {} "
                  .format(itemno, int(bitem.address), lsn,
                          XFS_LI_TYPES[li_type][7:]), end='')
            if li_type == XFS_LI_BUF:
                buf = item['bli_buf']
                flags = decode_flags(item['bli_flags'], XFS_BLI_FLAGS)
                print(" buf@{:x} bli_flags={}" .format(int(buf), flags))

                print("     {}".format(xfs_format_xfsbuf(buf)))
            elif li_type == XFS_LI_INODE:
                ili_flags = int(item['ili_lock_flags'])
                xfs_inode = item['ili_inode']
                print("inode@{:x} i_ino={} ili_lock_flags={:x} "
                      .format(int(xfs_inode['i_vnode'].address),
                              int(xfs_inode['i_ino']), ili_flags))
            elif li_type == XFS_LI_EFI:
                efi = item['efi_format']
                print("efi@{:x} size={}, nextents={}, id={:x}"
                      .format(int(item.address), int(efi['efi_size']),
                              int(efi['efi_nextents']), int(efi['efi_id'])))
            elif li_type == XFS_LI_EFI:
                efd = item['efd_format']
                print("efd@{:x} size={}, nextents={}, id={:x}"
                      .format(int(item.address), int(efd['efd_size']),
                              int(efd['efd_nextents']), int(efd['efd_id'])))
            elif li_type == XFS_LI_DQUOT:
                dquot = item['qli_dquot']
                flags = decode_flags(dquot['dq_flags'], XFS_DQ_FLAGS)
                print("dquot@{:x} flags={}".format(int(dquot), flags))
            elif li_type == XFS_LI_QUOTAOFF:
                qoff = item['qql_format']
                print("qoff@{:x} type={} size={} flags={}"
                      .format(int(qoff), int(qoff['qf_type']),
                              int(qoff['qf_size']), int(qoff['qf_flags'])))
            else:
                print("item@{:x}".format(int(item.address)))
            itemno += 1

    @classmethod
    def dump_buftarg(cls, targ: gdb.Value) -> None:
        for buf in list_for_each_entry(targ['bt_delwrite_queue'],
                                       types.xfs_buf_p_type.target(),
                                       'b_list'):
            print("{:x} {}".format(int(buf.address), xfs_format_xfsbuf(buf)))

    @classmethod
    def dump_buftargs(cls, args: Namespace):
        try:
            sb = get_super_block(args.addr)
        except gdb.NotAvailableError as e:
            raise CommandError(str(e))
        mp = xfs_mount(sb)
        ddev = mp['m_ddev_targp']
        ldev = mp['m_logdev_targp']

        print("Data device queue @ {:x}:".format(int(ddev)))
        cls.dump_buftarg(ddev)

        if int(ddev) != int(ldev):
            print("Log device queue:")
            cls.dump_buftarg(ldev)

    def execute(self, args):
        if hasattr(args, 'subcommand'):
            args.subcommand(args)
        else:
            raise CommandLineError("no command specified")

XFSCommand("xfs")
