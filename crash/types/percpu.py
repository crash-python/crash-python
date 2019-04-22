# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, Union, List, Tuple

import gdb
from crash.infra import CrashBaseClass, export
from crash.util import array_size, struct_has_member
from crash.types.list import list_for_each_entry
from crash.exceptions import DelayedAttributeError
from crash.types.bitmap import find_first_set_bit, find_last_set_bit
from crash.types.bitmap import find_next_set_bit, find_next_zero_bit
from crash.types.page import Page
from crash.types.cpu import highest_possible_cpu_nr

class PerCPUError(TypeError):
    fmt = "{} does not correspond to a percpu pointer."
    def __init__(self, var):
        super().__init__(self.fmt.format(var))

SymbolOrValue = Union[gdb.Value, gdb.Symbol]
PerCPUReturn = Union[gdb.Value, Dict[int, gdb.Value]]

class TypesPerCPUClass(CrashBaseClass):
    __types__ = [ 'void *', 'char *', 'struct pcpu_chunk',
                  'struct percpu_counter' ]
    __symvals__ = [ '__per_cpu_offset', 'pcpu_base_addr', 'pcpu_slot',
                    'pcpu_nr_slots', 'pcpu_group_offsets' ]
    __minsymvals__ = ['__per_cpu_start', '__per_cpu_end' ]
    __minsymbol_callbacks__ = [ ('__per_cpu_start', '_setup_per_cpu_size'),
                             ('__per_cpu_end', '_setup_per_cpu_size') ]
    __symbol_callbacks__ = [ ('__per_cpu_offset', '_setup_nr_cpus') ]

    dynamic_offset_cache: List[Tuple[int, int]] = list()
    static_ranges: Dict[int, int] = dict()
    last_cpu = -1
    nr_cpus = 0

    @classmethod
    def _setup_per_cpu_size(cls, symbol: gdb.Symbol) -> None:
        try:
            size = cls.__per_cpu_end - cls.__per_cpu_start
        except DelayedAttributeError:
            pass

        cls.static_ranges[0] = size
        if cls.__per_cpu_start != 0:
            cls.static_ranges[cls.__per_cpu_start] = size

        try:
            # This is only an optimization so we don't return NR_CPUS values
            # when there are far fewer CPUs on the system.
            cls.last_cpu = highest_possible_cpu_nr()
        except DelayedAttributeError:
            pass

    @classmethod
    def _setup_nr_cpus(cls, ignored: gdb.Symbol) -> None:
        cls.nr_cpus = array_size(cls.__per_cpu_offset)

        if cls.last_cpu == -1:
            cls.last_cpu = cls.nr_cpus

    @classmethod
    def _add_to_offset_cache(cls, base: int, start: int, end: int) -> None:
        cls.dynamic_offset_cache.append((base + start, base + end))

    @classmethod
    def dump_ranges(cls) -> None:
        """
        Dump all percpu ranges to stdout
        """
        for (start, size) in cls.static_ranges.items():
            print(f"static start={start:#x}, size={size:#x}")
        if cls.dynamic_offset_cache:
            for (start, end) in cls.dynamic_offset_cache:
                print(f"dynamic start={start:#x}, end={end:#x}")

    @classmethod
    def _setup_dynamic_offset_cache_area_map(cls, chunk: gdb.Value) -> None:
        used_is_negative = None
        chunk_base = int(chunk["base_addr"]) - int(cls.pcpu_base_addr)

        off = 0
        start = None
        _map = chunk['map']
        map_used = int(chunk['map_used'])

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
                val = int(_map[i])
                if val < 0:
                    used_is_negative = True
                    break

        if used_is_negative:
            for i in range(map_used):
                val = int(_map[i])
                if val < 0:
                    if start is None:
                        start = off
                else:
                    if start is not None:
                        cls._add_to_offset_cache(chunk_base, start, off)
                        start = None
                off += abs(val)
            if start is not None:
                cls._add_to_offset_cache(chunk_base, start, off)
        else:
            for i in range(map_used):
                off = int(_map[i])
                if off & 1 == 1:
                    off -= 1
                    if start is None:
                        start = off
                else:
                    if start is not None:
                        cls._add_to_offset_cache(chunk_base, start, off)
                        start = None
            if start is not None:
                off = int(_map[map_used]) - 1
                cls._add_to_offset_cache(chunk_base, start, off)


    @classmethod
    def _setup_dynamic_offset_cache_bitmap(cls, chunk: gdb.Value) -> None:
        group_offset = int(cls.pcpu_group_offsets[0])
        size_in_bytes = int(chunk['nr_pages']) * Page.PAGE_SIZE
        size_in_bits = size_in_bytes << 3
        start = -1
        end = 0

        chunk_base = int(chunk["base_addr"]) - int(cls.pcpu_base_addr)
        cls._add_to_offset_cache(chunk_base, 0, size_in_bytes)

    @classmethod
    def _setup_dynamic_offset_cache(cls) -> None:
        # TODO: interval tree would be more efficient, but this adds no 3rd
        # party module dependency...
        use_area_map = struct_has_member(cls.pcpu_chunk_type, 'map')
        for slot in range(cls.pcpu_nr_slots):
            for chunk in list_for_each_entry(cls.pcpu_slot[slot], cls.pcpu_chunk_type, 'list'):
                if use_area_map:
                    cls._setup_dynamic_offset_cache_area_map(chunk)
                else:
                    cls._setup_dynamic_offset_cache_bitmap(chunk)

    def _is_percpu_var_dynamic(self, var: int) -> bool:
        try:
            if not self.dynamic_offset_cache:
                self._setup_dynamic_offset_cache()

            # TODO: we could sort the list...
            for (start, end) in self.dynamic_offset_cache:
                if var >= start and var < end:
                    return True
        except DelayedAttributeError:
            # This can happen with the testcases or in kernels prior to 2.6.30
            pass

        return False

    # The resolved percpu address
    def _is_static_percpu_address(self, addr: int) -> bool:
        for start in self.static_ranges:
            size = self.static_ranges[start]
            for cpu in range(0, self.last_cpu):
                offset = int(__per_cpu_offset[cpu]) + start
                if addr >= offset and addr < offset + size:
                    return True
        return False

    # The percpu virtual address
    def is_static_percpu_var(self, addr: int) -> bool:
        """
        Returns whether the provided address is within the bounds of
        the percpu static ranges

        Args:
            addr (int): The address to query

        Returns:
            bool: whether this address belongs to a static range
        """
        for start in self.static_ranges:
            for cpu in range(0, self.last_cpu):
                size = self.static_ranges[start]
                if addr >= start and addr < start + size:
                    return True
        return False

    # The percpu range should start at offset 0 but gdb relocation
    # treats 0 as a special value indicating it should just be after
    # the previous section.  It's possible to override this while
    # loading debuginfo but not when debuginfo is embedded.
    def _relocated_offset(self, var):
        addr=int(var)
        start = self.__per_cpu_start
        size = self.static_ranges[start]
        if addr >= start and addr < start + size:
            return addr - start
        return addr

    @export
    def is_percpu_var(self, var: SymbolOrValue) -> bool:
        """
        Returns whether the provided value or symbol falls within
        any of the percpu ranges

        Args:
            var: (gdb.Value or gdb.Symbol): The value to query

        Returns:
            bool: whether the value belongs to any percpu range
        """
        if isinstance(var, gdb.Symbol):
            var = var.value().address

        var = int(var)
        if self.is_static_percpu_var(var):
            return True
        if self._is_percpu_var_dynamic(var):
            return True
        return False

    def get_percpu_var_nocheck(self, var: SymbolOrValue, cpu: int=None,
                               nr_cpus: int=None) -> PerCPUReturn:
        """
        Retrieve a per-cpu variable for one or all CPUs without performing
        range checks

        Per-cpus come in a few forms:
        - "Array" of objects
        - "Array" of pointers to objects
        - Pointers to either of those

        If we want to get the typing right, we need to recognize each one
        and figure out what type to pass back.  We do want to dereference
        pointer to a percpu but we don't want to dereference a percpu
        pointer.

        Args:
            var (gdb.Symbol, gdb.MinSymbol, gdb.Value):
                The value to use to resolve the percpu location
            cpu (int, optional, default=None): The cpu for which to return
                the per-cpu value.  A value of None will return a dictionary
                of [cpu, value] for all CPUs.
            nr_cpus(int, optional, default=None):

        Returns:
            gdb.Value<type>: If cpu is specified, the value corresponding to
                the specified CPU.
            dict(int, gdb.Value<type>): If cpu is not specified, the values
                corresponding to every CPU in a dictionary indexed by CPU
                number.

        Raises:
            TypeError: var is not gdb.Symbol or gdb.Value
            ValueError: cpu is less than 0
            ValueError: nr_cpus is less-or-equal to 0
        """
        if nr_cpus is None:
            nr_cpus = self.last_cpu
        if nr_cpus < 0:
            raise ValueError("nr_cpus must be > 0")
        if cpu is None:
            vals = {}
            for cpu in range(0, nr_cpus):
                vals[cpu] = self.get_percpu_var_nocheck(var, cpu, nr_cpus)
            return vals
        elif cpu < 0:
            raise ValueError("cpu must be >= 0")

        addr = self.__per_cpu_offset[cpu]
        if addr > 0:
            addr += self._relocated_offset(var)

        val = gdb.Value(addr).cast(var.type)
        if var.type != self.void_p_type:
            val = val.dereference()
        return val

    @export
    def get_percpu_var(self, var: SymbolOrValue, cpu: int=None,
                       nr_cpus: int=None) -> PerCPUReturn:
        """
        Retrieve a per-cpu variable for one or all CPUs

        Per-cpus come in a few forms:
        - "Array" of objects
        - "Array" of pointers to objects
        - Pointers to either of those

        If we want to get the typing right, we need to recognize each one
        and figure out what type to pass back.  We do want to dereference
        pointer to a percpu but we don't want to dereference a percpu
        pointer.

        Args:
            var (gdb.Symbol, gdb.MinSymbol, gdb.Value):
                The value to use to resolve the percpu location
            cpu (int, optional, default=None): The cpu for which to return
                the per-cpu value.  A value of None will return a dictionary
                of [cpu, value] for all CPUs.
            nr_cpus(int, optional, default=None):

        Returns:
            gdb.Value<type>: If cpu is specified, the value corresponding to
                the specified CPU.
            dict(int, gdb.Value<type>): If cpu is not specified, the values
                corresponding to every CPU in a dictionary indexed by CPU
                number.

        Raises:
            TypeError: var is not gdb.Symbol or gdb.Value
            PerCPUError: var does not fall into any percpu range
            ValueError: cpu is less than 0
            ValueError: nr_cpus is less-or-equal to 0
        """
        orig_var = var
        if isinstance(var, gdb.Symbol) or isinstance(var, gdb.MinSymbol):
            var = var.value()
        if not isinstance(var, gdb.Value):
            raise TypeError("Argument must be gdb.Symbol or gdb.Value")

        if var.type.code == gdb.TYPE_CODE_PTR:
            # The percpu contains pointers
            if var.address is not None and self.is_percpu_var(var.address):
                var = var.address
            # Pointer to a percpu
            elif self.is_percpu_var(var):
                if var.type != self.void_p_type:
                        var = var.dereference().address
                assert(self.is_percpu_var(var))
            else:
                raise PerCPUError(orig_var)
        # object is a percpu
        elif self.is_percpu_var(var.address):
                var = var.address
        else:
            raise PerCPUError(orig_var)

        return self.get_percpu_var_nocheck(var, cpu, nr_cpus)
