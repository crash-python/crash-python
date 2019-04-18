#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.types.list import list_for_each_entry
from crash.cache import CrashCache

class CrashCacheSlab(CrashCache):

    def __init__(self):
        super(CrashCacheSlab, self).__init__()
        self.populated = False
        self.kmem_caches = dict()
        self.kmem_caches_by_addr = dict()

    def refresh(self):
        self.populated = False
        self.kmem_caches = dict()
        self.kmem_caches_by_addr = dict()

cache = CrashCacheSlab()
