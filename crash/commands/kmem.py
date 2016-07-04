#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.commands import CrashCommand
from crash.cache import slab
from crash.types.slab import KmemCache, Slab
import argparse
import re

class KmemCommand(CrashCommand):
    """ kernel memory inspection

NAME
  TODO
    """

    def __init__(self, name):
        parser = argparse.ArgumentParser(prog=name)

        parser.add_argument('-s', action='store_true', default=False)

        parser.add_argument('arg', nargs=argparse.REMAINDER)

        parser.format_usage = lambda : "kmem [-s] [addr | slabname]\n"
        CrashCommand.__init__(self, name, parser)

    def execute(self, args):
        if args.s:
            cache_name = args.arg[0]
            cache = KmemCache.from_name(cache_name)
            cache.check_all()
            return
            
        for cache in slab.cache.get_kmem_caches().values():
            print cache.name

KmemCommand("kmem")
