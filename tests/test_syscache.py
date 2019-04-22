# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb
import sys
from importlib import reload

from crash.exceptions import DelayedAttributeError
fake_config = (
"""
#
# Linux kernel 4.4
#
CONFIG_HZ=250
# CONFIG_HZ_1000 is not set
#

""")

class TestSysCache(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-syscache")
        self.cycle_namespace()

    def tearDown(self):
        gdb.execute("file")

    def cycle_namespace(self):
        import crash.cache.syscache
        reload(crash.cache.syscache)
        self.CrashUtsnameCache = crash.cache.syscache.CrashUtsnameCache
        self.CrashConfigCache = crash.cache.syscache.CrashConfigCache
        self.CrashKernelCache = crash.cache.syscache.CrashKernelCache
        self.utsname = crash.cache.syscache.utsname
        self.kernel = crash.cache.syscache.kernel
        self.config = crash.cache.syscache.config

    def clear_namespace(self):
        gdb.execute("file")
        self.cycle_namespace()

    def get_fake_config(self):
        from crash.cache.syscache import CrashConfigCache
        class FakeConfigCache(CrashConfigCache):
            def decompress_config_buffer(self):
                self.config_buffer = fake_config
                return self.config_buffer

        return FakeConfigCache()

    def test_utsname_no_sym(self):
        gdb.execute("file")
        gdb.execute("maint flush-symbol-cache")
        self.cycle_namespace()
        utsname = self.CrashUtsnameCache()
        with self.assertRaises(DelayedAttributeError):
            release = utsname.release

    def test_utsname(self):
        utsname = self.CrashUtsnameCache()
        self.assertTrue(utsname.sysname == 'Linux')
        self.assertTrue(utsname.nodename == 'linux')
        self.assertTrue(utsname.release == '4.4.21-default')
        self.assertTrue(utsname.version == '#7 SMP Wed Nov 2 16:08:46 EDT 2016')
        self.assertTrue(utsname.machine == 'x86_64')
        self.assertTrue(utsname.domainname == 'suse.de')

    def test_utsname_namespace_nofile(self):
        self.clear_namespace()
        utsname = self.utsname
        with self.assertRaises(DelayedAttributeError):
            x = utsname.sysname

    def test_utsname_namespace(self):
        self.cycle_namespace()
        utsname = self.utsname
        self.assertTrue(utsname.sysname == 'Linux')
        self.assertTrue(utsname.nodename == 'linux')
        self.assertTrue(utsname.release == '4.4.21-default')
        self.assertTrue(utsname.version == '#7 SMP Wed Nov 2 16:08:46 EDT 2016')
        self.assertTrue(utsname.machine == 'x86_64')
        self.assertTrue(utsname.domainname == 'suse.de')

    # Kind of a silly test, but otherwise we need to have a real config
    def test_config(self):
        config = self.get_fake_config()
        self.assertTrue(str(config) == fake_config)

    def test_config_dict(self):
        config = self.get_fake_config()
        self.assertTrue(config['HZ'] == '250')

    def test_config_namespace(self):
        self.cycle_namespace()
        config = self.config
        from crash.cache.syscache import config
        x = str(config)

    def test_config_namespace_nofile(self):
        self.clear_namespace()
        from crash.cache.syscache import config
        with self.assertRaises(DelayedAttributeError):
            x = str(config)

    def test_config_dict_namespace(self):
        from crash.cache.syscache import config
        self.assertTrue(config['HZ'] == '250')

    def test_get_uptime_value(self):
        from crash.cache.syscache import CrashConfigCache, CrashKernelCache
        config = CrashConfigCache()
        kernel = CrashKernelCache(config)
        kernel.jiffies = 27028508
        kernel.adjust_jiffies = False
        x = kernel.uptime
        uptime = str(x)
        self.assertTrue(uptime == '1 day, 6:01:54')

    def test_get_uptime_with_symbol(self):
        from crash.cache.syscache import CrashKernelCache
        kernel = CrashKernelCache(self.get_fake_config())
        x = kernel.uptime

        self.assertTrue(str(x) == '0:02:34')

    def test_kernel_namespace(self):
        self.cycle_namespace()
        from crash.cache.syscache import kernel
        x = kernel.uptime

    def test_kernel_namespace_nofile(self):
        self.clear_namespace()
        from crash.cache.syscache import kernel
        with self.assertRaises(DelayedAttributeError):
            x = kernel.uptime

    def test_calculate_loadavg(self):
        config = self.CrashConfigCache()
        kernel = self.CrashKernelCache(config)
        self.assertTrue(kernel.calculate_loadavg(344) == 0.17)
        self.assertTrue(kernel.calculate_loadavg(105) == 0.05)
        self.assertTrue(kernel.calculate_loadavg(28) == 0.01)

        self.assertTrue(kernel.calculate_loadavg(458524) == 223.89)
        self.assertTrue(kernel.calculate_loadavg(455057) == 222.20)
        self.assertTrue(kernel.calculate_loadavg(446962) == 218.24)

    def test_loadavg_values(self):
        config = self.CrashConfigCache()
        kernel = self.CrashKernelCache(config)
        metrics = kernel.get_loadavg_values()
        self.assertTrue(metrics[0] == 0.17)
        self.assertTrue(metrics[1] == 0.05)
        self.assertTrue(metrics[2] == 0.01)

    def test_loadavg(self):
        config = self.CrashConfigCache()
        kernel = self.CrashKernelCache(config)
        x = kernel.loadavg
        self.assertTrue(x == "0.17 0.05 0.01")

    def test_loadavg_values_missing_symbol(self):
        self.clear_namespace()
        config = self.CrashConfigCache()
        kernel = self.CrashKernelCache(config)
        with self.assertRaises(DelayedAttributeError):
           metrics = kernel.get_loadavg_values()

    def test_loadavg_missing_symbol(self):
        self.clear_namespace()
        config = self.CrashConfigCache()
        kernel = self.CrashKernelCache(config)
        self.assertTrue(kernel.loadavg == "Unknown")

    def test_kernel_loadavg_namespace(self):
        self.cycle_namespace()
        from crash.cache.syscache import kernel
        x = kernel.loadavg
        self.assertTrue(x == "0.17 0.05 0.01")

    def test_kernel_loadavg_namespace_nofile(self):
        self.clear_namespace()
        from crash.cache.syscache import kernel
        self.assertTrue(kernel.loadavg == "Unknown")

