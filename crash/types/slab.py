#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of

kmem_cache_type = gdb.lookup_type('struct kmem_cache')

class KmemCache():
    gdb_obj = None

    num = 0
    buffer_size = 0
    name = ""

    def __init__(self, name, gdb_obj):
        self.name = name
        self.gdb_obj = gdb_obj
        
        self.num = int(gdb_obj["num"])
        self.buffer_size = int(gdb_obj["buffer_size"])

