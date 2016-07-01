# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import zlib
from crash.exceptions import MissingSymbolError
from crash.cache import CrashCache
from crash.infra import delayed_init

@delayed_init
class CrashUtsnameCache(CrashCache):
    def __init__(self):
        # Can't use super() with @delayed_init
        CrashCache.__init__(self)


        sym = gdb.lookup_global_symbol('init_uts_ns')
        if not sym:
            raise MissingSymbolError("CrashUtsnameCache requires init_uts_ns")
        init_uts_ns = sym.value()
        self.utsname = init_uts_ns['name']

        self.utsname_cache = {}

        for field in self.utsname.type.fields():
            val = self.utsname[field.name].string()
            self.utsname_cache[field.name] = val

    def __getattr__(self, name):
        if name in self.utsname_cache:
            return self.utsname_cache[name]
        raise AttributeError

@delayed_init
class CrashConfigCache(CrashCache):
    def __init__(self):
        CrashCache.__init__(self)

        self.uchar = gdb.lookup_type('unsigned char')
        self.ucharp = self.uchar.pointer()

    def __getattr__(self, name):
        if name == 'config_buffer':
            self.config_buffer = self.decompress_config_buffer()
            return self.config_buffer
        raise AttributeError

    @staticmethod
    def read_buf(address, size):
        return str(gdb.selected_inferior().read_memory(address, size))

    def decompress_config_buffer(self):
        MAGIC_START = 'IKCFG_ST'
        MAGIC_END = 'IKCFG_ED'
        GZIP_HEADER_LEN = 10

        sym = gdb.lookup_symbol('kernel_config_data',
                                block=None, domain=gdb.SYMBOL_VAR_DOMAIN)[0]
        if sym is None:
            raise MissingSymbolError("CrashConfigCache requires 'kernel_config_data' symbol.")
        kernel_config_data = sym.value()
        # Must cast it to ucharp to do the pointer arithmetic correctly
        data_addr = kernel_config_data.address.cast(self.ucharp)
        data_len = kernel_config_data.type.sizeof

        buf_len = len(MAGIC_START)
        buf = self.read_buf(data_addr, buf_len)
        if buf != MAGIC_START:
            raise IOError("Missing MAGIC_START in kernel_config_data.")

        buf_len = len(MAGIC_END)
        buf = self.read_buf(data_addr + data_len - buf_len - 1, buf_len)
        if buf != MAGIC_END:
            raise IOError("Missing MAGIC_END in kernel_config_data.")

        # Read the compressed data
        #
        # FIXME: We skip the gzip header (10 bytes) and decompress
        #        the data directly using zlib. If we know how to map
        #        the memory into a file/stream, it would be possible
        #        to use gzip module.
        buf_len = data_len - len(MAGIC_START) - len(MAGIC_END) - GZIP_HEADER_LEN
        buf = self.read_buf(data_addr + len(MAGIC_START) + GZIP_HEADER_LEN, buf_len)
        return zlib.decompress(buf, -15, buf_len)

    def __str__(self):
        return self.config_buffer

utsname = CrashUtsnameCache()
config = CrashConfigCache()
