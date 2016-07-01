# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb

from crash.cache.syscache import utsname, config, kernel
from crash.cache.syscache import CrashConfigCache

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

    def test_utsname(self):
        self.assertTrue(utsname.sysname == 'Linux')
        self.assertTrue(utsname.nodename == 'linux')
        self.assertTrue(utsname.release == '4.4.21-default')
        self.assertTrue(utsname.version == '#7 SMP Wed Nov 2 16:08:46 EDT 2016')
        self.assertTrue(utsname.machine == 'x86_64')
        self.assertTrue(utsname.domainname == 'suse.de')

    # Kind of a silly test, but otherwise we need to have a real config
    def test_config(self):
        class test_class(CrashConfigCache):
            def decompress_config_buffer(self):
                return fake_config

        x = test_class()
        self.assertTrue(str(x) == fake_config)

    def test_config_dict(self):
        class test_class(CrashConfigCache):
            def decompress_config_buffer(self):
                return fake_config

        x = test_class()
        self.assertTrue(x['HZ'] == '250')

    def test_get_uptime(self):
        x = kernel._get_uptime(250)
        self.assertTrue(x.seconds == 154)
        self.assertTrue(str(x) == '0:02:34')
