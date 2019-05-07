# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

gdbinit = """
set build-id-verbose 0
set python print-stack full
set prompt py-crash>
set height 0
set print pretty on"""

class TestModules(unittest.TestCase):
    def test_for_each_module(self):
        from crash.types.module import for_each_module

        modtype = gdb.lookup_type('struct module')

        for mod in for_each_module():
            self.assertTrue(mod.type == modtype)

    def test_for_each_module_section(self):
        from crash.types.module import for_each_module_section
        from crash.types.module import for_each_module

        for mod in for_each_module():
            for section in for_each_module_section(mod):
                self.assertTrue(type(section) is tuple)
                self.assertTrue(type(section[0]) is str)
                self.assertTrue(type(section[1]) is int)
