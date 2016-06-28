#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.commands import CrashCommand
from crash.cache import slab
import argparse
import re

class KmemCommand(CrashCommand):
    """ kernel memory inspection

NAME
  TODO
    """

    def __init__(self, name):
        parser = argparse.ArgumentParser(prog=name)

        parser.add_argument('-t', action='store_true', default=False)
        parser.add_argument('-d', action='store_true', default=False)
        parser.add_argument('-m', action='store_true', default=False)

        parser.format_usage = lambda : "log [-tdm]\n"
        CrashCommand.__init__(self, name, parser)

    def execute(self, args):
        slab.cache.init_kmem_caches()

KmemCommand("kmem")
