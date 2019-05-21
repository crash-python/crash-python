# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from argparse import Namespace
from crash.commands import Command, ArgumentParser
from crash.commands import CommandLineError
from crash.exceptions import DelayedAttributeError
from crash.subsystem.filesystem import for_each_super_block, super_fstype
from crash.subsystem.filesystem.btrfs import btrfs_fsid, btrfs_metadata_uuid

class BtrfsCommand(Command):
    """display Btrfs internal data structures

NAME
  btrfs - display Btrfs internal data structures

SYNOPSIS
  btrfs <command> <superblock>

COMMANDS
  btrfs list [-m] - list all btrfs file systems (-m to show metadata uuid)"""

    def __init__(self, name):
        parser = ArgumentParser(prog=name)
        subparsers = parser.add_subparsers(help="sub-command help")
        list_parser = subparsers.add_parser('list', help='list help')
        list_parser.set_defaults(subcommand=self.list_btrfs)
        list_parser.add_argument('-m', action='store_true', default=False)

        parser.format_usage = lambda: 'btrfs <subcommand> [args...]\n'
        Command.__init__(self, name, parser)

    def list_btrfs(self, args: Namespace) -> None:
        print_header = True
        count = 0
        for sb in for_each_super_block():
            if super_fstype(sb) == "btrfs":
                if args.m:
                    u = btrfs_metadata_uuid(sb)
                    which_fsid = "METADATA UUID"
                else:
                    u = btrfs_fsid(sb)
                    which_fsid = "FSID"
                if print_header:
                    print("SUPER BLOCK\t\tDEVICE\t\t{}".format(which_fsid))
                    print_header = False
                print("{}\t{}\t\t{}".format(sb.address, sb['s_id'].string(), u))
                count += 1
        if count == 0:
            print("No btrfs file systems were mounted.")

    def execute(self, args):
        if hasattr(args, 'subcommand'):
            args.subcommand(args)
        else:
            raise CommandLineError("no command specified")

BtrfsCommand("btrfs")
