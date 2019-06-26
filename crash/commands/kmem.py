#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Kernel memory inspection

::

  kmem addr             - try to find addr within kmem caches
  kmem -s [slabname]    - check consistency of single or all kmem cache
  kmem -z               - report zones
  kmem -V               - report vmstats

DESCRIPTION
-----------

This command currently offers very basic kmem cache query and checking.
"""

from typing import List

import argparse

from crash.commands import Command, ArgumentParser
from crash.commands import CommandError, CommandLineError
from crash.types.slab import kmem_cache_get_all, kmem_cache_from_name
from crash.types.slab import slab_from_obj_addr, KmemCacheNotFound
from crash.types.node import for_each_zone, for_each_populated_zone
from crash.types.vmstat import VmStat
from crash.util import get_symbol_value
from crash.exceptions import MissingSymbolError

class KmemCommand(Command):
    """ kernel memory inspection"""

    def __init__(self, name: str) -> None:
        parser = ArgumentParser(prog=name)

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-s', nargs='?', const=True, default=False,
                           dest='slabname')
        group.add_argument('-z', action='store_true', default=False)
        group.add_argument('-V', action='store_true', default=False)
        group.add_argument('address', nargs='?')

        super().__init__(name, parser)

    def execute(self, args: argparse.Namespace) -> None:
        if args.z:
            self.print_zones()
            return

        if args.V:
            self.print_vmstats()
            return

        if args.slabname:
            if args.slabname is True:
                print("Checking all kmem caches...")
                for cache in kmem_cache_get_all():
                    print(cache.name)
                    cache.check_all()
            else:
                cache_name = args.slabname
                print(f"Checking kmem cache {cache_name}")
                try:
                    cache = kmem_cache_from_name(cache_name)
                except KmemCacheNotFound:
                    raise CommandError(f"Cache {cache_name} not found.")
                cache.check_all()

            print("Checking done.")
            return

        if not args.address:
            raise CommandLineError("no address specified")

        try:
            addr = int(args.address, 0)
        except ValueError:
            raise CommandLineError("address must be numeric")
        slab = slab_from_obj_addr(addr)

        if not slab:
            raise CommandError("Address not found in any kmem cache.")

        (valid, obj, reason) = slab.contains_obj(addr)
        name = slab.kmem_cache.name

        if valid:
            (is_used, details) = slab.obj_in_use(obj)
            offset = addr - obj

            offset_str = "" if offset == 0 else f" offset {offset}/0x{offset:x}"
            details_str = "" if details is None else f" (in {details})"

            print(f"{'ALLOCATED' if is_used else 'FREE'}{details_str} "
                  f"object 0x{obj:x}{offset_str} from cache {name}")
        else:
            obj_str = ""
            if obj is not None:
                obj_str = f" object 0x{obj:x}"
            reason_str = ""
            if reason is not None:
                reason_str = f" ({reason})"
            print(f"INVALID address on slab {slab.gdb_obj.address} "
                  f"from cache {name}{obj_str}{reason_str}")

    def __print_vmstat(self, vmstat: List[int], diffs: List[int]) -> None:
        vmstat_names = VmStat.get_stat_names()
        just = max(map(len, vmstat_names))
        nr_items = VmStat.nr_stat_items

        vmstat = [sum(x) for x in zip(vmstat, diffs)]

        for i in range(0, nr_items):
            print("%s: %d (%d)" % (vmstat_names[i].rjust(just),
                                   vmstat[i], diffs[i]))

    def print_vmstats(self) -> None:
        try:
            vm_stat = get_symbol_value("vm_stat")
        except MissingSymbolError:
            raise CommandError("Support for new-style vmstat is unimplemented.")

        print("  VM_STAT:")
        #TODO put this... where?
        nr_items = VmStat.nr_stat_items

        stats = [0] * nr_items

        for item in range(0, nr_items):
            # TODO abstract atomic?
            stats[item] = int(vm_stat[item]["counter"])

        diffs = [0] * nr_items

        for zone in for_each_populated_zone():
            zone.add_vmstat_diffs(diffs)

        self.__print_vmstat(stats, diffs)

        print()
        print("  VM_EVENT_STATES:")

        vm_events = VmStat.get_events()
        names = VmStat.get_event_names()
        just = max(map(len, names))

        for name, val in zip(names, vm_events):
            print("%s: %d" % (name.rjust(just), val))

    def print_zones(self) -> None:
        for zone in for_each_zone():
            zone_struct = zone.gdb_obj

            print("NODE: %d  ZONE: %d  ADDR: %x  NAME: \"%s\"" %
                  (int(zone_struct["node"]), zone.zid,
                   int(zone_struct.address), zone_struct["name"].string()))

            if not zone.is_populated():
                print("  [unpopulated]")
                print()
                continue

            print("  VM_STAT:")
            vmstat = zone.get_vmstat()
            diffs = zone.get_vmstat_diffs()
            self.__print_vmstat(vmstat, diffs)

            print()

KmemCommand("kmem")
