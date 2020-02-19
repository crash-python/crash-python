#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Kernel memory inspection

::

  kmem [-s] [-S] addr    - information about address
  kmem -s [cache]        - check consistency of single or all kmem cache
  kmem -S[SS...] [cache] - list details / objects in a single or all kmem caches
  kmem -z                - report zones
  kmem -V                - report vmstats

DESCRIPTION
-----------

This command currently offers very basic kmem cache query and checking.
Currently it reports whether addr is a struct page, or slab object. If
it's a slab object, the -s parameter will tell more about the slab page
and the -S parameter will list all objects on the same slab page.

The -s and -S parameters can be also used with a kmem cache name or
address, to check consistency or list details. If no cache is name is
given, it will check/list all caches. The -S parameter can be repeated
multiple times (up to 4), increasing the verbosity of listing.

The -S parameter currently only works for SLUB kernels.
"""

from typing import List, Optional

import argparse

from crash.commands import Command, ArgumentParser
from crash.commands import CommandError, CommandLineError
from crash.types.slab import kmem_cache_get_all, kmem_cache_from_name,\
                             kmem_cache_from_addr, KmemCache
from crash.types.slab import slab_from_obj_addr, KmemCacheNotFound,\
                             slab_from_page
from crash.types.node import for_each_zone, for_each_populated_zone
from crash.types.page import safe_page_from_page_addr
from crash.types.vmstat import VmStat
from crash.util import get_symbol_value, safe_int
from crash.exceptions import MissingSymbolError

class KmemCommand(Command):
    """ kernel memory inspection"""

    def __init__(self, name: str) -> None:
        parser = ArgumentParser(prog=name)

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-s', action='store_true', default=False,
                           dest='slabcheck')
        group.add_argument('-S', action="count", dest='slablist')
        group.add_argument('-z', action='store_true', default=False)
        group.add_argument('-V', action='store_true', default=False)
        parser.add_argument('address', nargs='?')

        super().__init__(name, parser)

    def _find_kmem_cache(self, query: str) -> Optional[KmemCache]:
        cache = None
        try:
            cache = kmem_cache_from_name(query)
        except KmemCacheNotFound:
            addr = safe_int(query)
            if addr is not None:
                try:
                    cache = kmem_cache_from_addr(addr)
                except KmemCacheNotFound:
                    pass
        return cache

    def execute(self, args: argparse.Namespace) -> None:
        if args.z:
            self.print_zones()
            return

        if args.V:
            self.print_vmstats()
            return

        cache = None
        if args.slabcheck:
            if args.address is None:
                print("Checking all kmem caches...")
                for cache in kmem_cache_get_all():
                    print(cache.name)
                    cache.check_all()
                print("Checking done.")
                return
            cache_name = args.address
            cache = self._find_kmem_cache(cache_name)
            if cache is not None:
                print(f"Checking kmem cache {cache_name}")
                cache.check_all()
                print("Checking done.")
                return

        if args.slablist:
            if args.address is None:
                print("Listing all kmem caches...")
                for cache in kmem_cache_get_all():
                    cache.list_all(args.slablist)
                return
            cache_name = args.address
            cache = self._find_kmem_cache(cache_name)
            if cache is not None:
                cache.list_all(args.slablist)
                return

        if not args.address:
            raise CommandLineError("no address specified")

        addr = safe_int(args.address)
        if addr is None:
            raise CommandLineError("address must be numeric")

        slab = None
        page = safe_page_from_page_addr(addr)
        if page is not None:
            #TODO improve
            print(f"0x{addr:x} belongs to a struct page 0x{page.address:x} "
                  f"pfn {page.pfn}")

            if page.compound_head().is_slab():
                slab = slab_from_page(page)
                name = slab.kmem_cache.name
                if args.slabcheck or args.slablist:
                    print(f"page belongs to cache {name} slab "
                          f"{slab.short_header()}")
                    if args.slablist:
                        print("")
                        print(f"Slab details: {slab.long_header()}")
                        slab.print_objects()
                return
        else:
            slab = slab_from_obj_addr(addr)
            if not slab:
                raise CommandError(f"Kmem cache not found: '{args.address}' is not "
                                   f"a valid name of a kmem cache or an address "
                                   f"known to the kmem subsystem.")
        if slab is None:
            return

        (valid, obj, reason) = slab.contains_obj(addr)
        name = slab.kmem_cache.name

        if valid:
            (is_used, details) = slab.obj_in_use(obj)
            offset = addr - obj

            offset_str = "" if offset == 0 else f" offset 0x{offset:x} ({offset})"
            details_str = "" if details is None else f" (in {details})"
            objsize = slab.kmem_cache.object_size
            state = "ALLOCATED" if is_used else "FREE"

            print(f"{state}{details_str} object 0x{obj:x}{offset_str} "
                  f"size 0x{objsize:x} ({objsize}) from cache {name} "
                  f"slab {slab.short_header()}")
        else:
            obj_str = ""
            if obj is not None:
                obj_str = f" object 0x{obj:x}"
            reason_str = ""
            if reason is not None:
                reason_str = f" ({reason})"
            print(f"INVALID address on slab {slab.gdb_obj.address} "
                  f"from cache {name}{obj_str}{reason_str}")
        if args.slablist:
            print("")
            print(f"Slab details: {slab.long_header()}")
            slab.print_objects()

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

            zone.check_free_pages()

KmemCommand("kmem")
