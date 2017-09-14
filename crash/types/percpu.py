# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
from crash.infra import delayed_init, exporter, export
from crash.util import array_size

if sys.version_info.major >= 3:
    long = int

@exporter
@delayed_init
class TypesPerCPUClass(object):
    def __init__(self):
        self.charp = gdb.lookup_type('char').pointer()

        pcpu_offset = gdb.lookup_global_symbol('__per_cpu_offset')
        self.per_cpu_offset_value = pcpu_offset.value()

        # Really only helpful for testing since it's always 0 in the kernel
        pcpu_start = gdb.lookup_minimal_symbol('__per_cpu_start')
        self.per_cpu_start = long(pcpu_start.value())
        pcpu_end = gdb.lookup_minimal_symbol('__per_cpu_end')
        self.per_cpu_end = long(pcpu_end.value())
        self.per_cpu_size = self.per_cpu_end - self.per_cpu_start
        self.nr_cpus = array_size(self.per_cpu_offset_value)

    def __is_percpu_var(self, var):
        if long(var) < self.per_cpu_start:
            return False
        v = var.cast(self.charp) - self.per_cpu_start
        return long(v) < self.per_cpu_size

    @export
    def is_percpu_var(self, var):
        if isinstance(var, gdb.Symbol):
            var = var.value().address
        return self.__is_percpu_var(var)

    def get_percpu_var_nocheck(self, var, cpu=None):
        if cpu is None:
            vals = {}
            for cpu in range(0, self.nr_cpus):
                vals[cpu] = self.get_percpu_var_nocheck(var, cpu)
            return vals

        addr = self.per_cpu_offset_value[cpu]
        addr += var.cast(self.charp)
        addr -= self.per_cpu_start
        vartype = var.type
        return addr.cast(vartype).dereference()

    @export
    def get_percpu_var(self, var, cpu=None):
        if isinstance(var, gdb.Symbol):
            try:
                var = long(var.value())
            except:
                var = var.value().address
        if not (isinstance(var, gdb.Value) and
                var.type.code == gdb.TYPE_CODE_PTR):
            raise TypeError("Argument must be gdb.Symbol or gdb.Value describing a pointer {}".format(type(var)))
        if not self.is_percpu_var(var):
            raise TypeError("Argument does not correspond to a percpu pointer.")
        return self.get_percpu_var_nocheck(var, cpu)
