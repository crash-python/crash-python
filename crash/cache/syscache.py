# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, List, Any

import re
import zlib
from datetime import timedelta

from crash.exceptions import DelayedAttributeError
from crash.cache import CrashCache
from crash.util import array_size
from crash.util.symbols import Types, Symvals, SymbolCallbacks, MinimalSymvals
from crash.infra.lookup import DelayedValue

import gdb

ImageLocation = Dict[str, Dict[str, int]]

class CrashUtsnameCache(CrashCache):
    symvals = Symvals(['init_uts_ns'])

    def __init__(self) -> None:
        self._utsname_cache_dict: Dict[str, str] = dict()

    @property
    def utsname(self) -> gdb.Value:
        return self.symvals.init_uts_ns['name']

    def _init_utsname_cache(self) -> None:
        d = self._utsname_cache_dict

        for field in self.utsname.type.fields():
            val = self.utsname[field.name].string()
            d[field.name] = val

    @property
    def _utsname_cache(self) -> Dict[str, str]:
        if not self._utsname_cache_dict:
            self._init_utsname_cache()

        return self._utsname_cache_dict

    def _utsname_field(self, name: str) -> str:
        try:
            return self._utsname_cache[name]
        except KeyError:
            raise DelayedAttributeError(name)

    @property
    def sysname(self) -> str:
        return self._utsname_field('sysname')

    @property
    def nodename(self) -> str:
        return self._utsname_field('nodename')

    @property
    def release(self) -> str:
        return self._utsname_field('release')

    @property
    def version(self) -> str:
        return self._utsname_field('version')

    @property
    def machine(self) -> str:
        return self._utsname_field('machine')

    @property
    def domainname(self) -> str:
        return self._utsname_field('domainname')

class CrashConfigCache(CrashCache):
    types = Types(['char *'])
    symvals = Symvals(['kernel_config_data'])
    msymvals = MinimalSymvals(['kernel_config_data',
                               'kernel_config_data_end'])

    def __init__(self) -> None:
        self._config_buffer = ""
        self._ikconfig_cache: Dict[str, str] = dict()

    @property
    def config_buffer(self) -> str:
        if not self._config_buffer:
            self._config_buffer = self._decompress_config_buffer()
        return self._config_buffer

    @property
    def ikconfig_cache(self) -> Dict[str, str]:
        if not self._ikconfig_cache:
            self._parse_config()
        return self._ikconfig_cache

    def __getitem__(self, name: str) -> Any:
        try:
            return self.ikconfig_cache[name]
        except KeyError:
            return None

    @staticmethod
    def _read_buf_bytes(address: int, size: int) -> bytes:
        return gdb.selected_inferior().read_memory(address, size).tobytes()

    def _locate_config_buffer_section(self) -> ImageLocation:
        data_start = int(self.msymvals.kernel_config_data)
        data_end = int(self.msymvals.kernel_config_data_end)

        return {
            'data' : {
                'start' : data_start,
                'size' : data_end - data_start,
            },
            'magic' : {
                'start' : data_start - 8,
                'end' : data_end,
            },
        }

    def _locate_config_buffer_typed(self) -> ImageLocation:
        start = int(self.symvals.kernel_config_data.address)
        end = start + self.symvals.kernel_config_data.type.sizeof

        return {
            'data' : {
                'start' : start + 8,
                'size' : end - start - 2*8 - 1,
            },
            'magic' : {
                'start' : start,
                'end' : end - 8 - 1,
            },
        }

    def _verify_image(self, location: ImageLocation) -> None:
        magic_start = b'IKCFG_ST'
        magic_end = b'IKCFG_ED'

        buf_len = len(magic_start)
        buf = self._read_buf_bytes(location['magic']['start'], buf_len)
        if buf != magic_start:
            raise IOError(f"Missing magic_start in kernel_config_data. Got `{buf}'")

        buf_len = len(magic_end)
        buf = self._read_buf_bytes(location['magic']['end'], buf_len)
        if buf != magic_end:
            raise IOError("Missing magic_end in kernel_config_data. Got `{buf}'")

    def _decompress_config_buffer(self) -> str:
        try:
            location = self._locate_config_buffer_section()
        except DelayedAttributeError:
            location = self._locate_config_buffer_typed()

        self._verify_image(location)

        # Read the compressed data
        buf = self._read_buf_bytes(location['data']['start'],
                                   location['data']['size'])

        return zlib.decompress(buf, 16 + zlib.MAX_WBITS).decode('utf-8')

    def __str__(self) -> str:
        return self.config_buffer

    def _parse_config(self) -> None:
        for line in self.config_buffer.splitlines():
            # bin comments
            line = re.sub("#.*$", "", line).strip()

            if not line:
                continue

            m = re.match("CONFIG_([^=]*)=(.*)", line)
            if m:
                self._ikconfig_cache[m.group(1)] = m.group(2)

class CrashKernelCache(CrashCache):
    symvals = Symvals(['avenrun'])

    _adjust_jiffies = False
    _reset_uptime = True

    _jiffies_dv = DelayedValue('jiffies')

    def __init__(self, config_cache: CrashConfigCache) -> None:
        CrashCache.__init__(self)
        self.config = config_cache
        self._hz = -1
        self._uptime = timedelta(seconds=0)
        self._loadavg = ""

    @property
    def jiffies(self) -> int:
        v = self._jiffies_dv.get()
        return v

    @property
    def hz(self) -> int:
        if self._hz == -1:
            self._hz = int(self.config['HZ'])

        return self._hz

    def get_uptime(self) -> timedelta:
        return self.uptime

    @property
    def uptime(self) -> timedelta:
        if self._uptime == 0 or self._reset_uptime:
            uptime = self._adjusted_jiffies() // self.hz
            self._uptime = timedelta(seconds=uptime)
            self._reset_uptime = False
        return self._uptime

    @property
    def loadavg(self) -> str:
        if not self._loadavg:
            try:
                metrics = self._get_loadavg_values()
                self._loadavg = self._format_loadavg(metrics)
            except DelayedAttributeError:
                return "Unknown"
        return self._loadavg

    def _calculate_loadavg(self, metric: int) -> float:
        # The kernel needs to do fixed point trickery to calculate
        # a floating point average.  We can just return a float.
        return round(int(metric) / (1 << 11), 2)

    def _format_loadavg(self, metrics: List[float]) -> str:
        out = []
        for metric in metrics:
            out.append(str(metric))

        return " ".join(out)

    def _get_loadavg_values(self) -> List[float]:
        metrics = []
        for index in range(0, array_size(self.symvals.avenrun)):
            metrics.append(self._calculate_loadavg(self.symvals.avenrun[index]))

        return metrics

    @classmethod
    def set_jiffies(cls, value: int) -> None:
        cls._jiffies_dv.value = None
        cls._jiffies_dv.callback(value)
        cls._reset_uptime = True

    @classmethod
    # pylint: disable=unused-argument
    def setup_jiffies(cls, symbol: gdb.Symbol) -> bool:
        jiffies_sym = gdb.lookup_global_symbol('jiffies_64')

        if jiffies_sym:
            try:
                jiffies = int(jiffies_sym.value())
            except gdb.MemoryError:
                return False
            cls._adjust_jiffies = True
        else:
            jiffies_sym = gdb.lookup_global_symbol('jiffies')
            if not jiffies_sym:
                return False
            jiffies = int(jiffies_sym.value())
            cls._adjust_jiffies = False

        cls.set_jiffies(jiffies)

        return True

    def _adjusted_jiffies(self) -> int:
        if self._adjust_jiffies:
            return self.jiffies -(int(0x100000000) - 300 * self.hz)
        return self.jiffies

symbol_cbs = SymbolCallbacks([('jiffies', CrashKernelCache.setup_jiffies),
                              ('jiffies_64', CrashKernelCache.setup_jiffies)])

utsname = CrashUtsnameCache()
config = CrashConfigCache()
kernel = CrashKernelCache(config)

def jiffies_to_msec(jiffies: int) -> int:
    return 1000 // kernel.hz * jiffies
