# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

from crash.types.percpu import get_percpu_vars, is_percpu_var

class TestPerCPU(unittest.TestCase):
    def test_runqueues(self):
        rqs = gdb.lookup_symbol('runqueues', None)[0]
        rq_type = gdb.lookup_type('struct rq')

        self.assertTrue(rqs.type == rq_type)

        pcpu = get_percpu_vars(rqs)
        for (cpu, rq) in pcpu.items():
            self.assertTrue(type(cpu) is int)
            self.assertTrue(type(rq) is gdb.Value)
            self.assertTrue(rq.type == rq_type)
