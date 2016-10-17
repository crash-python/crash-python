#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

ulong_type = gdb.lookup_type("unsigned long")
bits_per_ulong = ulong_type.sizeof * 8

def for_each_set_bit(bitmap):
    size = bitmap.type.sizeof * 8
    idx = 0
    bit = 0
    while size > 0:
        ulong = bitmap[idx]

        if ulong != 0:
            for off in range(min(size, bits_per_ulong)):
                if ulong & 1 != 0:
                    yield bit
                bit += 1
                ulong >>= 1
        else:
            bit += bits_per_ulong

        size -= bits_per_ulong
        idx += 1
    
