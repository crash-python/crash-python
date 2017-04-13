# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb

from crash.exceptions import MissingSymbolError
from crash.cache.syscache import CrashUtsnameCache
from crash.cache.syscache import CrashConfigCache
from crash.cache.syscache import CrashKernelCache

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

    def cycle_namespace(self):
        import crash.cache.syscache
        reload(crash.cache.syscache)

    def clear_namespace(self):
        gdb.execute("file")
        self.cycle_namespace()

    def get_fake_config(self):
        class FakeConfigCache(CrashConfigCache):
            def decompress_config_buffer(self):
                self.config_buffer = fake_config

        return FakeConfigCache()

    def test_utsname_no_sym(self):
        gdb.execute("file")
        utsname = CrashUtsnameCache()
        with self.assertRaises(MissingSymbolError):
            release = utsname.release

    def test_utsname(self):
        utsname = CrashUtsnameCache()
        self.assertTrue(utsname.sysname == 'Linux')
        self.assertTrue(utsname.nodename == 'linux')
        self.assertTrue(utsname.release == '4.4.21-default')
        self.assertTrue(utsname.version == '#7 SMP Wed Nov 2 16:08:46 EDT 2016')
        self.assertTrue(utsname.machine == 'x86_64')
        self.assertTrue(utsname.domainname == 'suse.de')

    def test_utsname_namespace_nofile(self):
        self.clear_namespace()
        from crash.cache.syscache import utsname
        with self.assertRaises(MissingSymbolError):
            x = utsname.sysname

    def test_utsname_namespace(self):
        self.cycle_namespace()
        from crash.cache.syscache import utsname
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
        from crash.cache.syscache import config
        x = str(config)

    def test_config_namespace_nofile(self):
        self.clear_namespace()
        from crash.cache.syscache import config
        with self.assertRaises(MissingSymbolError):
            x = str(config)

    def test_config_dict_namespace(self):
        from crash.cache.syscache import config
        self.assertTrue(config['HZ'] == '250')

    def test_get_uptime_value(self):
        config = CrashConfigCache()
        class FakeKernelCache(CrashKernelCache):
            def load_jiffies(self):
                self.jiffies = 27028508
        kernel = FakeKernelCache(config)
        x = kernel.uptime

        self.assertTrue(str(x) == '1 day, 6:01:54')

    def test_get_uptime_with_symbol(self):
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
        with self.assertRaises(MissingSymbolError):
            x = kernel.uptime
