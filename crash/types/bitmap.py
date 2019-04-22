#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.infra import CrashBaseClass, export

class TypesBitmapClass(CrashBaseClass):
    __types__ = [ 'unsigned long' ]
    __type_callbacks__ = [ ('unsigned long', 'setup_ulong') ]

    bits_per_ulong = None

    @classmethod
    def setup_ulong(cls, gdbtype):
        cls.bits_per_ulong = gdbtype.sizeof * 8

    @export
    @classmethod
    def for_each_set_bit(cls, bitmap):

        # FIXME: callback not workie?
        cls.bits_per_ulong = cls.unsigned_long_type.sizeof * 8

        size = bitmap.type.sizeof * 8
        idx = 0
        bit = 0
        while size > 0:
            ulong = bitmap[idx]

            if ulong != 0:
                for off in range(min(size, cls.bits_per_ulong)):
                    if ulong & 1 != 0:
                        yield bit
                    bit += 1
                    ulong >>= 1
            else:
                bit += cls.bits_per_ulong

            size -= cls.bits_per_ulong
            idx += 1
    
