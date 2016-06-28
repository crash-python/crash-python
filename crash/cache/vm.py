# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb

from crash.cache import CrashCache
class CrashCacheVM(CrashCache):
    def __init__(self):
        super(CrashCacheVM, self).__init__()

    def refresh(self):
        pass

cache = CrashCacheVM()
