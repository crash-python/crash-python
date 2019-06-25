# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import argparse

from crash.commands import Command, ArgumentParser
from crash.commands import CommandLineError, CommandError
from crash.subsystem.filesystem.kernfs import find_kn, for_each_child
from crash.subsystem.filesystem.kernfs import KERNFS_DIR, KERNFS_LINK

import gdb

class KernfsCommand(Command):

    def __init__(self, name: str) -> None:
        parser = ArgumentParser(prog=name)

        subparsers = parser.add_subparsers()
        ls_parser = subparsers.add_parser('ls')
        ls_parser.set_defaults(subcommand=self.command_ls)
        ls_parser.add_argument('kn', type=ArgumentParser.address)
        ls_parser.add_argument('-R', type=int, default=0)
        ls_parser.add_argument('-f', action='store_false', default=True)

        super().__init__(name, parser)

    def command_ls(self, args: argparse.Namespace) -> None:
        kn = find_kn(args.kn)
        if not kn['flags'] & KERNFS_DIR:
            raise CommandError("{} is not a kernfs directory".format(args.kn))

        print("{:^6} {:^6} {:^32} {:^16}".format(
            "flags", "mode", "name", "kernfs_node"))
        self._ls_dir(kn, args.R, args)

    def _ls_dir(self, kn: gdb.Value, depth: int, args: argparse.Namespace, prefix: str = '') -> None:
        prefix += kn['name'].string() + '/'
        print(f"{prefix}:")

        children = for_each_child(kn)
        if args.f:
            children = sorted(children,
                              key=lambda kn: (not kn['flags'] & KERNFS_DIR,
                                              kn['name'].string()))

        subdirs = []
        for ckn in children:
            if ckn['flags'] & KERNFS_DIR:
                subdirs.append(ckn)
            self.show_one_kn(ckn, args)
        print()

        if depth != 0:
            for dkn in subdirs:
                self._ls_dir(dkn, depth - 1, args, prefix)

    # pylint: disable=unused-argument
    def show_one_kn(self, kn: gdb.Value, args: argparse.Namespace) -> None:
        print("    {}{}    {:>03o} {:32} {:016x}".format(
            'd' if kn['flags'] & KERNFS_DIR else ' ',
            'l' if kn['flags'] & KERNFS_LINK else ' ',
            int(kn['mode']) & 0x1ff,
            kn['name'].string(),
            int(kn.address)
        ))

    def execute(self, args: argparse.Namespace) -> None:
        if hasattr(args, 'subcommand'):
            args.subcommand(args)
        else:
            raise CommandLineError("no command specified")

KernfsCommand("kernfs")
