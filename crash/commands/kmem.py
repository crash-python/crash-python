#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import crash
from crash.commands import CrashCommand
from crash.cache import slab
from crash.types.slab import KmemCache, Slab
from crash.types.zone import Zone
import argparse
import re

class KmemCommand(CrashCommand):
    """ kernel memory inspection

NAME
  kmem - kernel memory inspection

SYNOPSIS
  kmem addr             - try to find addr within kmem caches
  kmem -s [slabname]    - check consistency of single or all kmem cache

DESCRIPTION
  This command currently offers very basic kmem cache query and checking.
    """

    def __init__(self, name):
        parser = argparse.ArgumentParser(prog=name)

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-s', action='store_true', default=False)
        group.add_argument('-z', action='store_true', default=False)

        parser.add_argument('arg', nargs=argparse.REMAINDER)

        parser.format_usage = lambda : "kmem [-s] [addr | slabname]\n"
        CrashCommand.__init__(self, name, parser)

    def execute(self, args):
        if args.z:
            self.print_zones()
            return
        elif args.s:
            if args.arg:
                cache_name = args.arg[0]
                print "Checking kmem cache " + cache_name
                cache = KmemCache.from_name(cache_name)
                cache.check_all()
            else:
                print "Checking all kmem caches..."  
                for cache in crash.cache.slab.cache.get_kmem_caches().values():
                    print cache.name
                    cache.check_all()

            print "Checking done."
            return
          
        if not args.arg:
            print "Nothing to do."
            return

        addr = long(args.arg[0], 0)
        slab = Slab.from_obj(addr)

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

    def print_zones(self):
       for zone in Zone.for_each():
            zone_struct = zone.gdb_obj
            
            print("NODE: %d  ZONE: %d  ADDR: %x  NAME: \"%s\"" %
                    (zone_struct["node"], zone.zid, zone_struct.address,
                                    zone_struct["name"].string()))
                
KmemCommand("kmem")
