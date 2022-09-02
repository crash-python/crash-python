# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Display character and block devices

  -d    display information about disks
"""

import argparse

from crash.commands import Command, ArgumentParser
from crash.subsystem.storage import for_each_disk, gendisk_name
from crash.subsystem.storage.block import queue_request_stats
class DevCommand(Command):
    """display character and block devices"""

    def __init__(self, name: str) -> None:
        parser = ArgumentParser(prog=name)

        parser.add_argument('-d', action='store_true', default=False,
                            required=True)

        super().__init__(name, parser)

    def execute(self, args: argparse.Namespace) -> None:
        if args.d:
            print("{:^5} {:^16} {:^10} {:^16} {:^5} {:^5} {:^5} {:^5}"
                  .format("MAJOR", "GENDISK", "NAME", "REQUEST_QUEUE",
                          "TOTAL", "ASYNC", "SYNC", "DRV"))
            for disk in for_each_disk():
                stats = queue_request_stats(disk['queue'])
                print("{:5d} {:016x} {:<10} {:016x} {:5d} {:5d} {:5d} {:5d}"
                      .format(int(disk['major']), int(disk.address),
                              gendisk_name(disk), int(disk['queue']),
                              stats[0] + stats[1], stats[0], stats[1],
                              stats[2] + stats[3]))

DevCommand("dev")
