# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
from crash.infra import CrashBaseClass, export
from crash.util import array_size
from crash.exceptions import DelayedAttributeError

if sys.version_info.major >= 3:
    long = int

class TypesPerCPUClass(CrashBaseClass):
    __types__ = [ 'char *' ]
    __symvals__ = [ '__per_cpu_offset' ]
    __minsymvals__ = ['__per_cpu_start', '__per_cpu_end' ]
    __minsymbol_callbacks__ = [ ('__per_cpu_start', 'setup_per_cpu_size'),
                             ('__per_cpu_end', 'setup_per_cpu_size') ]
    __symbol_callbacks__ = [ ('__per_cpu_offset', 'setup_nr_cpus') ]

    @classmethod
    def setup_per_cpu_size(cls, symbol):
        try:
            cls.per_cpu_size = cls.__per_cpu_end - cls.__per_cpu_start
        except DelayedAttributeError:
            pass

    @classmethod
    def setup_nr_cpus(cls, ignored):
        cls.nr_cpus = array_size(cls.__per_cpu_offset)

    def __is_percpu_var(self, var):
        if long(var) < self.__per_cpu_start:
            return False
        v = var.cast(self.char_p_type) - self.__per_cpu_start
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

        addr = self.__per_cpu_offset[cpu]
        addr += var.cast(self.char_p_type)
        addr -= self.__per_cpu_start
        vartype = var.type
        return addr.cast(vartype).dereference()

    @export
    def get_percpu_var(self, var, cpu=None):
        # Percpus can be:
        # - actual objects, where we'll need to use the address.
        # - pointers to objects, where we'll need to use the target
        # - a pointer to a percpu object, where we'll need to use the
        #   address of the target
        if isinstance(var, gdb.Symbol):
            var = var.value()
        if not isinstance(var, gdb.Value):
            raise TypeError("Argument must be gdb.Symbol or gdb.Value")
        if var.type.code != gdb.TYPE_CODE_PTR:
            var = var.address
        if not self.is_percpu_var(var):
            var = var.address
        if not self.is_percpu_var(var):
            raise TypeError("Argument does not correspond to a percpu pointer.")
        return self.get_percpu_var_nocheck(var, cpu)
