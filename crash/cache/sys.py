#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import re
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
    ikconfig_cache = None
    machdep_cache = None
    kernel_cache = None

    def read_buf(self, address, size):
        buf_raw = gdb.selected_inferior().read_memory(address, size)
        if isinstance(buf_raw, memoryview):
            return buf_raw.tobytes()
        else:
            return str(buf_raw)

    def init_utsname_cache(self):
        if self.utsname_cache:
            return

        try:
            init_uts_ns = gdb.lookup_global_symbol('init_uts_ns').value()
            utsname = init_uts_ns['name']
        except Exception as e:
            print("Error: Unable to locate utsname: %s" % (e))
            raise GetSymbolException(e)

        try:
            self.utsname_cache = dict()
            self.utsname_cache['nodename'] = utsname['nodename'].string()
            self.utsname_cache['release'] = utsname['release'].string()
            self.utsname_cache['version'] = utsname['version'].string()
            self.utsname_cache['machine'] = utsname['machine'].string()
        except Exception as e:
            print("Error: Unable to locate utsname string: %s" % (e))
            raise GetValueException(e)


    def init_ikconfig_raw_cache(self):
        if self.ikconfig_raw_cache:
            return

        MAGIC_START = b'IKCFG_ST'
        MAGIC_END = b'IKCFG_ED'
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

        self.ikconfig_raw_cache = zlib.decompress(buf, -15, buf_len).decode('ascii')


    def init_ikconfig_cache(self):
        if self.ikconfig_cache:
            return

        if not self.ikconfig_raw_cache:
            self.init_ikconfig_raw_cache()

        self.ikconfig_cache = dict()

        for line in self.ikconfig_raw_cache.splitlines():
            # bin comments
            line = re.sub("#.*$", "", line)
            # bin white space at the beginning and the end of the line
            line = re.sub("^\s*", "", line)
            line = re.sub("\s*$", "", line)

            if not line:
                continue

            items = re.split("=", line)
            if len(items) == 2:
                self.ikconfig_cache[items[0]] = items[1]
            else:
                print("Warning: did not parse kernel config line: %s" % (line))


    def convert_time(self, jiffies):
        SEC_MINUTES = 60
        SEC_HOURS = 60 * SEC_MINUTES
        SEC_DAYS = 24 * SEC_HOURS

        total = jiffies / self.machdep_cache['hz']

        days = total / SEC_DAYS
        total %= SEC_DAYS
        hours = total / SEC_HOURS
        total %= SEC_HOURS
        minutes = total / SEC_MINUTES
        seconds = total % SEC_MINUTES

        buf = ""
        if days:
            buf = "%d days, " % (days)
        buf += "%02d:%02d:%02d" % (hours, minutes, seconds)

        return buf

    def get_uptime(self):
        jiffies = gdb.lookup_global_symbol('jiffies_64').value()
        if jiffies:
            # FIXME: Only kernel above 2.6.0 initializes 64-bit jiffies
            #        value by 2^32 + 5 minutes
            jiffies -= long(0x100000000) - 300 * self.machdep_cache['hz']
        else:
            jiffies = gdb.lookup_global_symbol('jiffies').value()

        return self.convert_time(jiffies)


    def init_machdep_cache(self):
        if self.machdep_cache:
            return

        if not self.ikconfig_cache:
            self.init_ikconfig_cache()

        self.machdep_cache = dict()
        self.machdep_cache["hz"] = long(self.ikconfig_cache["CONFIG_HZ"])


    def init_kernel_cache(self):
        if self.kernel_cache:
            return

        if not self.machdep_cache:
            self.init_machdep_cache()

        self.kernel_cache = dict()
        self.kernel_cache["uptime"] = self.get_uptime()


    def init_sys_caches(self):
        self.init_utsname_cache()
        self.init_kernel_cache()

    def __init__(self):
        super(CrashCacheSys, self).__init__()

    def refresh(self):
        pass

cache = CrashCacheSys()
