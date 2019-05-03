# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from builtins import round

import gdb
import re
import zlib
from datetime import timedelta

from crash.exceptions import DelayedAttributeError
from crash.cache import CrashCache
from crash.util import array_size
from crash.util.symbols import Types, Symvals, SymbolCallbacks
from crash.infra.lookup import DelayedValue

class CrashUtsnameCache(CrashCache):
    symvals = Symvals([ 'init_uts_ns' ])

    def load_utsname(self):
        self.utsname = self.symvals.init_uts_ns['name']
        return self.utsname

    def init_utsname_cache(self):
        d = {}

        for field in self.utsname.type.fields():
            val = self.utsname[field.name].string()
            d[field.name] = val

        self.utsname_cache = d
        return self.utsname_cache

    utsname_fields = [ 'sysname', 'nodename', 'release',
                       'version', 'machine', 'domainname' ]
    def __getattr__(self, name):
        if name == 'utsname_cache':
            return self.init_utsname_cache()
        elif name == 'utsname':
            return self.load_utsname()
        if name in self.utsname_fields:
            return self.utsname_cache[name]
        return getattr(self.__class__, name)

class CrashConfigCache(CrashCache):
    types = Types([ 'char *' ])
    symvals = Symvals([ 'kernel_config_data' ])

    def __getattr__(self, name):
        if name == 'config_buffer':
            return self.decompress_config_buffer()
        elif name == 'ikconfig_cache':
            return self._parse_config()
        return getattr(self.__class__, name)

    @staticmethod
    def read_buf(address, size):
        return gdb.selected_inferior().read_memory(address, size)

    @staticmethod
    def read_buf_str(address, size):
        buf = gdb.selected_inferior().read_memory(address, size)
        if isinstance(buf, memoryview):
            return buf.tobytes().decode('utf-8')
        else:
            return str(buf)

    def decompress_config_buffer(self):
        MAGIC_START = 'IKCFG_ST'
        MAGIC_END = 'IKCFG_ED'

        # Must cast it to char * to do the pointer arithmetic correctly
        data_addr = self.symvals.kernel_config_data.address.cast(self.types.char_p_type)
        data_len = self.symvals.kernel_config_data.type.sizeof

        buf_len = len(MAGIC_START)
        buf = self.read_buf_str(data_addr, buf_len)
        if buf != MAGIC_START:
            raise IOError("Missing MAGIC_START in kernel_config_data.")

        buf_len = len(MAGIC_END)
        buf = self.read_buf_str(data_addr + data_len - buf_len - 1, buf_len)
        if buf != MAGIC_END:
            raise IOError("Missing MAGIC_END in kernel_config_data.")

        # Read the compressed data
        buf_len = data_len - len(MAGIC_START) - len(MAGIC_END)
        buf = self.read_buf(data_addr + len(MAGIC_START), buf_len)
        self.config_buffer = zlib.decompress(buf, 16 + zlib.MAX_WBITS)
        if (isinstance(self.config_buffer, bytes)):
            self.config_buffer = str(self.config_buffer.decode('utf-8'))
        else:
            self.config_buffer = str(self.config_buffer)
        return self.config_buffer

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

        return self.ikconfig_cache

    def __getitem__(self, name):
        try:
            return self.ikconfig_cache[name]
        except KeyError:
            return None

class CrashKernelCache(CrashCache):
    symvals = Symvals([ 'avenrun' ])

    jiffies_ready = False
    adjust_jiffies = False

    jiffies_dv = DelayedValue('jiffies')

    @property
    def jiffies(self):
        v = self.jiffies_dv.get()
        return v

    def __init__(self, config):
        CrashCache.__init__(self)
        self.config = config

    def __getattr__(self, name):
        if name == 'hz':
            self.hz = int(self.config['HZ'])
            return self.hz
        elif name == 'uptime':
            return self.get_uptime()
        elif name == 'loadavg':
            return self.get_loadavg()
        return getattr(self.__class__, name)

    @staticmethod
    def calculate_loadavg(metric):
        # The kernel needs to do fixed point trickery to calculate
        # a floating point average.  We can just return a float.
        return round(int(metric) / (1 << 11), 2)

    @staticmethod
    def format_loadavg(metrics):
        out = []
        for metric in metrics:
            out.append(str(metric))

        return " ".join(out)

    def get_loadavg_values(self):
        metrics = []
        for index in range(0, array_size(self.symvals.avenrun)):
            metrics.append(self.calculate_loadavg(self.symvals.avenrun[index]))

        return metrics

    def get_loadavg(self):
        try:
            metrics = self.get_loadavg_values()
            self.loadavg = self.format_loadavg(metrics)
            return self.loadavg
        except DelayedAttributeError:
            return "Unknown"

    @classmethod
    def set_jiffies(cls, value):
        cls.jiffies_dv.value = None
        cls.jiffies_dv.callback(value)

    @classmethod
    def setup_jiffies(cls, symbol):
        if cls.jiffies_ready:
            return

        jiffies_sym = gdb.lookup_global_symbol('jiffies_64')

        if jiffies_sym:
            try:
                jiffies = int(jiffies_sym.value())
            except gdb.MemoryError:
                return False
            cls.adjust_jiffies = True
        else:
            jiffies = int(gdb.lookup_global_symbol('jiffies').value())
            cls.adjust_jiffies = False

        cls.set_jiffies(jiffies)

    def adjusted_jiffies(self):
        if self.adjust_jiffies:
            return self.jiffies -(int(0x100000000) - 300 * self.hz)
        else:
            return self.jiffies

    def get_uptime(self):
        self.uptime = timedelta(seconds=self.adjusted_jiffies() // self.hz)
        return self.uptime

symbol_cbs = SymbolCallbacks( [( 'jiffies',
                                 CrashKernelCache.setup_jiffies ),
                               ( 'jiffies_64',
                                 CrashKernelCache.setup_jiffies ) ])

utsname = CrashUtsnameCache()
config = CrashConfigCache()
kernel = CrashKernelCache(config)

def jiffies_to_msec(jiffies):
    return 1000 // kernel.hz * jiffies
