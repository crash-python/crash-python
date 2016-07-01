#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import zlib
from crash.cache import CrashCache

class GetSymbolException(Exception):
    pass

class GetValueException(Exception):
    pass

uchar = gdb.lookup_type('unsigned char')
ucharp = uchar.pointer()

class CrashCacheSys(CrashCache):

    utsname_cache = None
    ikconfig_raw_cache = None

    def read_buf(self, address, size):
        return str(gdb.selected_inferior().read_memory(address, size))

    def init_utsname_cache(self):
        if self.utsname_cache:
            return

        try:
            init_uts_ns = gdb.lookup_global_symbol('init_uts_ns').value()
            utsname = init_uts_ns['name']
        except Exception, e:
            print "Error: Unable to locate utsname: %s" % (e)
            raise GetSymbolException(e)

        try:
            self.utsname_cache = dict()
            self.utsname_cache['nodename'] = utsname['nodename'].string()
            self.utsname_cache['release'] = utsname['release'].string()
            self.utsname_cache['version'] = utsname['version'].string()
            self.utsname_cache['machine'] = utsname['machine'].string()
        except Exception, e:
            print "Error: Unable to locate utsname string: %s" % (e)
            raise GetValueException(e)


    def init_ikconfig_raw_cache(self):
        if self.ikconfig_raw_cache:
            return

        MAGIC_START = 'IKCFG_ST'
        MAGIC_END = 'IKCFG_ED'
        GZIP_HEADER_LEN = 10

        kernel_config_data_sym = gdb.lookup_symbol('kernel_config_data', block=None, domain=gdb.SYMBOL_VAR_DOMAIN)[0]
        kernel_config_data = kernel_config_data_sym.value()
        # Must cast it to ucharp to do the pointer arithmetic correctly
        data_addr = kernel_config_data.address.cast(ucharp)
        data_len = kernel_config_data_sym.type.sizeof

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

        self.ikconfig_raw_cache = zlib.decompress(buf, -15, buf_len)

    def init_sys_caches(self):
        self.init_utsname_cache()
        self.init_ikconfig_raw_cache()

    def __init__(self):
        super(CrashCacheSys, self).__init__()

    def refresh(self):
        pass

cache = CrashCacheSys()
