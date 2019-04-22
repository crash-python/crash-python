#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import crash
from crash.commands import CrashCommand, CrashCommandParser
from crash.types.slab import kmem_cache_get_all, kmem_cache_from_name, slab_from_obj_addr
from crash.types.zone import for_each_zone, for_each_populated_zone
from crash.types.vmstat import VmStat
import argparse
import re

def getValue(sym):
    return gdb.lookup_symbol(sym, None)[0].value()

class KmemCommand(CrashCommand):
    """ kernel memory inspection

NAME
  kmem - kernel memory inspection

SYNOPSIS
  kmem addr             - try to find addr within kmem caches
  kmem -s [slabname]    - check consistency of single or all kmem cache
  kmem -z               - report zones
  kmem -V               - report vmstats

DESCRIPTION
  This command currently offers very basic kmem cache query and checking.
    """

    def __init__(self, name):
        parser = CrashCommandParser(prog=name)

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-s', action='store_true', default=False)
        group.add_argument('-z', action='store_true', default=False)
        group.add_argument('-V', action='store_true', default=False)

        parser.add_argument('arg', nargs=argparse.REMAINDER)

        parser.format_usage = lambda : "kmem [-s] [addr | slabname]\n"
        super(KmemCommand, self).__init__(name, parser)

    def execute(self, args):
        if args.z:
            self.print_zones()
            return
        elif args.V:
            self.print_vmstats()
            return
        elif args.s:
            if args.arg:
                cache_name = args.arg[0]
                print "Checking kmem cache " + cache_name
                cache = kmem_cache_from_name(cache_name)
                if cache is None:
                    print "Cache {} not found.".format(cache_name)
                    return
                cache.check_all()
            else:
                print "Checking all kmem caches..."  
                for cache in kmem_cache_get_all():
                    print cache.name
                    cache.check_all()

            print "Checking done."
            return
          
        if not args.arg:
            print "Nothing to do."
            return

        addr = long(args.arg[0], 0)
        slab = slab_from_obj_addr(addr)

        if not slab:
            print "Address not found in any kmem cache."
            return

        obj = slab.contains_obj(addr)
        name = slab.kmem_cache.name

        if obj[0]:
            print ("ALLOCATED object %x from slab %s" % (obj[1], name))
        else:
            if obj[1] == 0L:
                print ("Address on slab %s but not within valid object slot"
                                % name)
            elif not obj[2]:
                print ("FREE object %x from slab %s" % (obj[1], name))
            else:
                ac = obj[2]
                if ac["ac_type"] == "percpu":
                    ac_desc = "cpu %d cache" % ac["nid_tgt"]
                elif ac["ac_type"] == "shared":
                    ac_desc = "shared cache on node %d" % ac["nid_tgt"]
                elif ac["ac_type"] == "alien":
                    ac_desc = "alien cache of node %d for node %d" % (ac["nid_src"], ac["nid_tgt"])
                else:
                    print "unexpected array cache type"
                    print ac
                    return
                    
                print ("FREE object %x from slab %s (in %s)" %
                                           (obj[1], name, ac_desc))

    def __print_vmstat(self, vmstat, diffs):
        vmstat_names = VmStat.get_stat_names();
        just = max(map(len, vmstat_names))
        nr_items = VmStat.nr_stat_items

        vmstat = [sum(x) for x in zip(vmstat, diffs)]

        for i in range(0, nr_items):
            print("%s: %d (%d)" % (vmstat_names[i].rjust(just),
                                                vmstat[i], diffs[i]))

    def print_vmstats(self):
        print "  VM_STAT:"
        #TODO put this... where?
        nr_items = VmStat.nr_stat_items
    
        stats = [0L] * nr_items
        vm_stat = getValue("vm_stat")

        for item in range (0, nr_items):
            # TODO abstract atomic?
            stats[item] = long(vm_stat[item]["counter"])

        diffs = [0L] * nr_items

        for zone in for_each_populated_zone():
            zone.add_vmstat_diffs(diffs)

        self.__print_vmstat(stats, diffs)

        print
        print "  VM_EVENT_STATES:"

        vm_events = VmStat.get_events()
        names = VmStat.get_event_names()
        just = max(map(len, names))
    
        for name, val in zip(names, vm_events):
            print("%s: %d" % (name.rjust(just), val))

    def print_zones(self):
        for zone in for_each_zone():
            zone_struct = zone.gdb_obj
            
            print("NODE: %d  ZONE: %d  ADDR: %x  NAME: \"%s\"" %
                    (zone_struct["node"], zone.zid, zone_struct.address,
                                    zone_struct["name"].string()))

            if not zone.is_populated():
                print "  [unpopulated]"
                print
                continue

            print "  VM_STAT:"
            vmstat = zone.get_vmstat()
            diffs = zone.get_vmstat_diffs()
            self.__print_vmstat(vmstat, diffs)

            print
                
KmemCommand("kmem")
