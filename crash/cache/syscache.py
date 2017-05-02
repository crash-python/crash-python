# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import round

import gdb
import re
import zlib
import sys
from datetime import timedelta

if sys.version_info.major >= 3:
    long = int

from crash.exceptions import MissingSymbolError
from crash.cache import CrashCache
from crash.util import array_size

class CrashUtsnameCache(CrashCache):
    def load_utsname(self):
        sym = gdb.lookup_global_symbol('init_uts_ns')
        if not sym:
            raise MissingSymbolError("CrashUtsnameCache requires init_uts_ns")
        init_uts_ns = sym.value()
        self.utsname = init_uts_ns['name']
        return self.utsname

    def init_utsname_cache(self):
        self.utsname_cache = {}

        for field in self.utsname.type.fields():
            val = self.utsname[field.name].string()
            self.utsname_cache[field.name] = val

        return self.utsname_cache

    def __getattr__(self, name):
        if name == 'utsname_cache':
            return self.init_utsname_cache()
        elif name == 'utsname':
            return self.load_utsname()
        if name in self.utsname_cache:
            return self.utsname_cache[name]
        raise AttributeError

class CrashConfigCache(CrashCache):
    __types__ = [ 'char *' ]
    __symvals__ = [ 'kernel_config_data' ]

    def __getattr__(self, name):
        if name == 'config_buffer':
            self.decompress_config_buffer()
        elif name == 'ikconfig_cache':
            self._parse_config()
        else:
            raise AttributeError
        return getattr(self, name)

    @staticmethod
    def read_buf(address, size):
        return str(gdb.selected_inferior().read_memory(address, size))

    def decompress_config_buffer(self):
        MAGIC_START = 'IKCFG_ST'
        MAGIC_END = 'IKCFG_ED'
        GZIP_HEADER_LEN = 10

        # Must cast it to char * to do the pointer arithmetic correctly
        data_addr = self.kernel_config_data.address.cast(self.char_p_type)
        data_len = self.kernel_config_data.type.sizeof

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
        self.config_buffer = zlib.decompress(buf, -15, buf_len)

    def __str__(self):
        return self.config_buffer

    def _parse_config(self):
        self.ikconfig_cache = {}

        for line in self.config_buffer.splitlines():
            # bin comments
            line = re.sub("#.*$", "", line).strip()

            if not line:
                continue

            m = re.match("CONFIG_([^=]*)=(.*)", line)
            if m:
                self.ikconfig_cache[m.group(1)] = m.group(2)

    def __getitem__(self, name):
        return self.ikconfig_cache[name]

class CrashKernelCache(CrashCache):
    def __init__(self, config):
        CrashCache.__init__(self)
        self.config = config

    def __getattr__(self, name):
        if name == 'hz':
            self.hz = long(self.config['HZ'])
        elif name == 'uptime':
            self.uptime = self.get_uptime()
        elif name == 'jiffies':
            self.load_jiffies()
        elif name == 'loadavg':
            self.loadavg = self.get_loadavg()
        else:
            raise AttributeError

        return getattr(self, name)

    @staticmethod
    def calculate_loadavg(metric):
        # The kernel needs to do fixed point trickery to calculate
        # a floating point average.  We can just return a float.
        return round(long(metric) / (1 << 11), 2)

    @staticmethod
    def format_loadavg(metrics):
        out = []
        for metric in metrics:
            out.append(str(metric))

        return " ".join(out)

    def get_loadavg_values(self):
        sym = gdb.lookup_global_symbol('avenrun')
        if not sym:
            raise MissingSymbolError("loadavg values require 'avenrun'")

        avenrun = sym.value()
        metrics = []
        for index in range(0, array_size(avenrun)):
            metrics.append(self.calculate_loadavg(avenrun[index]))

        return metrics

    def get_loadavg(self):
        try:
            metrics = self.get_loadavg_values()
            return self.format_loadavg(metrics)
        except MissingSymbolError:
            return "Unknown"

    def load_jiffies(self):
        jiffies_sym = gdb.lookup_global_symbol('jiffies_64')
        if jiffies_sym:
            jiffies = long(jiffies_sym.value())
            # FIXME: Only kernel above 2.6.0 initializes 64-bit jiffies
            #        value by 2^32 + 5 minutes
            jiffies -= long(0x100000000) - 300 * self.hz
        else:
            jiffies_sym = gdb.lookup_global_symbol('jiffies')
            if jiffies_sym:
                jiffies = long(jiffies_sym.value())

        if jiffies_sym is None:
            raise MissingSymbolError("Could not locate jiffies_64 or jiffies")

        self.jiffies = jiffies

    def get_uptime(self):
        return timedelta(seconds=self.jiffies // self.hz)

    def jiffies_to_msec(self, jiffies):
        return 1000 // self.hz * jiffies

utsname = CrashUtsnameCache()
config = CrashConfigCache()
kernel = CrashKernelCache(config)
