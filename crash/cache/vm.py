#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import gdb

from crash.cache import CrashCache
class CrashCacheVM(CrashCache):
    def __init__(self):
        super(CrashCacheVM, self).__init__()

    def refresh(self):
        pass

cache = CrashCacheVM()
