# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
from crash.infra import CrashBaseClass, export
from crash.util import array_size
from crash.types.list import list_for_each_entry
from crash.exceptions import DelayedAttributeError

if sys.version_info.major >= 3:
    long = int

class TypesPerCPUClass(CrashBaseClass):
    __types__ = [ 'char *', 'struct pcpu_chunk' ]
    __symvals__ = [ '__per_cpu_offset', 'pcpu_base_addr', 'pcpu_slot',
                    'pcpu_nr_slots' ]
    __minsymvals__ = ['__per_cpu_start', '__per_cpu_end' ]
    __minsymbol_callbacks__ = [ ('__per_cpu_start', 'setup_per_cpu_size'),
                             ('__per_cpu_end', 'setup_per_cpu_size') ]
    __symbol_callbacks__ = [ ('__per_cpu_offset', 'setup_nr_cpus') ]

    dynamic_offset_cache = None

    @classmethod
    def setup_per_cpu_size(cls, symbol):
        try:
            cls.per_cpu_size = cls.__per_cpu_end - cls.__per_cpu_start
        except DelayedAttributeError:
            pass

    @classmethod
    def setup_nr_cpus(cls, ignored):
        cls.nr_cpus = array_size(cls.__per_cpu_offset)

    @classmethod
    def __setup_dynamic_offset_cache(cls):
        # TODO: interval tree would be more efficient, but this adds no 3rd
        # party module dependency...
        cls.dynamic_offset_cache = list()
        used_is_negative = None
        for slot in range(cls.pcpu_nr_slots):
            for chunk in list_for_each_entry(cls.pcpu_slot[slot], cls.pcpu_chunk_type, 'list'):
                chunk_base = long(chunk["base_addr"]) - long(cls.pcpu_base_addr) + long(cls.__per_cpu_start)
                off = 0
                start = None
                _map = chunk['map']
                map_used = long(chunk['map_used'])

                # Prior to 3.14 commit 723ad1d90b56 ("percpu: store offsets
                # instead of lengths in ->map[]"), negative values in map
                # meant the area is used, and the absolute value is area size.
                # After the commit, the value is area offset for unused, and
                # offset | 1 for used (all offsets have to be even). The value
                # at index 'map_used' is a 'sentry' which is the total size |
                # 1. There is no easy indication of whether kernel includes
                # the commit, unless we want to rely on version numbers and
                # risk breakage in case of backport to older version. Instead
                # employ a heuristic which scans the first chunk, and if no
                # negative value is found, assume the kernel includes the
                # commit.
                if used_is_negative is None:
                    used_is_negative = False
                    for i in range(map_used):
                        val = long(_map[i])
                        if val < 0:
                            used_is_negative = True
                            break

                if used_is_negative:
                    for i in range(map_used):
                        val = long(_map[i])
                        if val < 0:
                            if start is None:
                                start = off
                        else:
                            if start is not None:
                                cls.__add_to_offset_cache(chunk_base, start, off)
                                start = None
                        off += abs(val)
                    if start is not None:
                        cls.__add_to_offset_cache(chunk_base, start, off)
                else:
                    for i in range(map_used):
                        off = long(_map[i])
                        if off & 1 == 1:
                            off -= 1
                            if start is None:
                                start = off
                        else:
                            if start is not None:
                                cls.__add_to_offset_cache(chunk_base, start, off)
                                start = None
                    if start is not None:
                        off = long(_map[map_used]) - 1
                        cls.__add_to_offset_cache(chunk_base, start, off)

    def __is_percpu_var(self, var):
        if long(var) < self.__per_cpu_start:
            return False
        v = var.cast(self.char_p_type) - self.__per_cpu_start
        return long(v) < self.per_cpu_size

    def __is_percpu_var_dynamic(self, var):
        if self.dynamic_offset_cache is None:
            self.__setup_dynamic_offset_cache()

        var = long(var)
        # TODO: we could sort the list...
        for (start, end) in self.dynamic_offset_cache:
            if var >= start and var < end:
                return True

        return False

    @export
    def is_percpu_var(self, var):
        if isinstance(var, gdb.Symbol):
            var = var.value().address
        if self.__is_percpu_var(var):
            return True
        if self.__is_percpu_var_dynamic(var):
            return True
        return False

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
