# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb

from crash.cache.syscache import utsname

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
