# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.cache import CrashCache
class CrashCacheVM(CrashCache):
    def __init__(self):
        super(CrashCacheVM, self).__init__()

    def refresh(self):
        pass

cache = CrashCacheVM()
