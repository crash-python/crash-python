# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import gdb

import crash
import crash.types.percpu as percpu

class TestPerCPU(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-percpu", to_string=True)

        try:
            print()
            print("--- Unsuppressable gdb output ---", end='')

            gdb.execute("run", to_string=False)
            msym = gdb.lookup_minimal_symbol('__per_cpu_load')
            self.baseaddr = msym.value().address
            self.test_struct = gdb.lookup_type("struct test_struct")
            self.ulong_type = gdb.lookup_type("long unsigned int")
            self.voidp = gdb.lookup_type("void").pointer()
        except gdb.error as e:
            # If we don't tear it down, the rest of the tests in
            # other files will fail due to it using the wrong core file
            self.tearDown()
            raise(e)

    def tearDown(self):
        try:
            gdb.execute("detach", to_string=True)
            gdb.execute("file")
        except gdb.error:
            print()
            pass
        print("--- End gdb output ---")

    def test_struct_test(self):
        var = gdb.lookup_symbol('struct_test', None)[0]
        self.assertTrue(var is not None)
        for cpu, val in list(percpu.get_percpu_vars(var).items()):
            self.assertTrue(val['x'] == cpu)
            self.assertTrue(val.type == self.test_struct)

    def test_ulong_test(self):
        var = gdb.lookup_symbol('ulong_test', None)[0]
        self.assertTrue(var is not None)
        for cpu, val in list(percpu.get_percpu_vars(var).items()):
            self.assertTrue(val == cpu)
            self.assertTrue(val.type == self.ulong_type)

    def test_ulong_ptr_test(self):
        var = gdb.lookup_symbol('ptr_to_ulong_test', None)[0]
        self.assertTrue(var is not None)
        for cpu, val in list(percpu.get_percpu_vars(var).items()):
            self.assertTrue(val.type == self.ulong_type.pointer())
            self.assertTrue(val.dereference() == cpu)

    def test_voidp_test(self):
        var = gdb.lookup_symbol('voidp_test', None)[0]
        self.assertTrue(var is not None)
        for cpu, val in list(percpu.get_percpu_vars(var).items()):
            self.assertTrue(val is not None)
            self.assertTrue(val.type == self.voidp)
            self.assertTrue(int(val) == 0xdeadbeef)

    def test_struct_test_ptr(self):
        var = gdb.lookup_symbol('ptr_to_struct_test', None)[0]
        self.assertTrue(var is not None)
        for cpu, val in list(percpu.get_percpu_vars(var).items()):
            self.assertTrue(val['x'] == cpu)
            self.assertTrue(val.type == self.test_struct.pointer())

    # This is a saved pointer to an unbound percpu var
    def test_percpu_ptr_sym(self):
        var = gdb.lookup_symbol('percpu_test', None)[0]
        self.assertTrue(var is not None)
        for cpu, val in list(percpu.get_percpu_vars(var).items()):
            self.assertTrue(val.type == self.test_struct)

    # This is a pointer to an unbound percpu var
    def test_percpu_ptr_val(self):
        var = gdb.lookup_symbol('percpu_test', None)[0].value()
        self.assertTrue(var is not None)
        for cpu, val in list(percpu.get_percpu_vars(var).items()):
            self.assertTrue(val.type == self.test_struct)

    # This is a saved pointer to an bound percpu var (e.g. normal ptr)
    def test_non_percpu_sym(self):
        var = gdb.lookup_symbol('non_percpu_test', None)[0]
        self.assertTrue(var is not None)
        with self.assertRaises(TypeError):
            x = percpu.get_percpu_var(var, 0)
        self.assertTrue(var.value()['x'] == 0)

    # This is a pointer to an bound percpu var (e.g. normal ptr)
    def test_non_percpu_ptr(self):
        var = gdb.lookup_symbol('non_percpu_test', None)[0].value()
        self.assertTrue(var is not None)
        with self.assertRaises(TypeError):
            x = percpu.get_percpu_var(var, 0)
        self.assertTrue(var['x'] == 0)
