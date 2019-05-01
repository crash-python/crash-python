# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, Union, List, Tuple

import gdb
from crash.infra import CrashBaseClass, export
from crash.util import array_size, struct_has_member
from crash.types.list import list_for_each_entry
from crash.types.module import for_each_module
from crash.exceptions import DelayedAttributeError
from crash.types.bitmap import find_first_set_bit, find_last_set_bit
from crash.types.bitmap import find_next_set_bit, find_next_zero_bit
from crash.types.page import Page
from crash.types.cpu import highest_possible_cpu_nr

class PerCPUError(TypeError):
    """The passed object does not respond to a percpu pointer."""
    _fmt = "{} does not correspond to a percpu pointer."
    def __init__(self, var):
        super().__init__(self._fmt.format(var))

SymbolOrValue = Union[gdb.Value, gdb.Symbol]

class TypesPerCPUClass(CrashBaseClass):
    """
    Per-cpus come in a few forms:
    - "Array" of objects
    - "Array" of pointers to objects
    - Pointers to either of those

    If we want to get the typing right, we need to recognize each one
    and figure out what type to pass back.  We do want to dereference
    pointer to a percpu but we don't want to dereference a percpu
    pointer.
    """
    __types__ = [ 'void *', 'char *', 'struct pcpu_chunk',
                  'struct percpu_counter' ]
    __symvals__ = [ '__per_cpu_offset', 'pcpu_base_addr', 'pcpu_slot',
                    'pcpu_nr_slots', 'pcpu_group_offsets' ]
    __minsymvals__ = ['__per_cpu_start', '__per_cpu_end' ]
    __minsymbol_callbacks__ = [ ('__per_cpu_start', '_setup_per_cpu_size'),
                             ('__per_cpu_end', '_setup_per_cpu_size') ]
    __symbol_callbacks__ = [ ('__per_cpu_offset', '_setup_nr_cpus') ]

    _dynamic_offset_cache: List[Tuple[int, int]] = list()
    _static_ranges: Dict[int, int] = dict()
    _module_ranges: Dict[int, int] = dict()
    _last_cpu = -1
    _nr_cpus = 0

    @classmethod
    def _setup_per_cpu_size(cls, symbol: gdb.Symbol) -> None:
        try:
            size = cls.__per_cpu_end - cls.__per_cpu_start
        except DelayedAttributeError:
            pass

        cls._static_ranges[0] = size
        if cls.__per_cpu_start != 0:
            cls._static_ranges[cls.__per_cpu_start] = size

        try:
            # This is only an optimization so we don't return NR_CPUS values
            # when there are far fewer CPUs on the system.
            cls._last_cpu = highest_possible_cpu_nr()
        except DelayedAttributeError:
            pass

    @classmethod
    def _setup_nr_cpus(cls, ignored: gdb.Symbol) -> None:
        cls._nr_cpus = array_size(cls.__per_cpu_offset)

        if cls._last_cpu == -1:
            cls._last_cpu = cls._nr_cpus

    @classmethod
    def _setup_module_ranges(cls, modules: gdb.Symbol) -> None:
        for module in for_each_module():
            start = int(module['percpu'])
            if start == 0:
                continue

            size = int(module['percpu_size'])
            cls._module_ranges[start] = size

    @classmethod
    def _add_to_offset_cache(cls, base: int, start: int, end: int) -> None:
        cls._dynamic_offset_cache.append((base + start, base + end))

    @classmethod
    def dump_ranges(cls) -> None:
        """
        Dump all percpu ranges to stdout
        """
        for (start, size) in cls._static_ranges.items():
            print(f"static start={start:#x}, size={size:#x}")
        for (start, size) in cls._module_ranges.items():
            print(f"module start={start:#x}, size={size:#x}")
        if cls._dynamic_offset_cache:
            for (start, end) in cls._dynamic_offset_cache:
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
            if not self._dynamic_offset_cache:
                self._setup_dynamic_offset_cache()

            # TODO: we could sort the list...
            for (start, end) in self._dynamic_offset_cache:
                if var >= start and var < end:
                    return True
        except DelayedAttributeError:
            # This can happen with the testcases or in kernels prior to 2.6.30
            pass

        return False

    # The resolved percpu address
    def _is_static_percpu_address(self, addr: int) -> bool:
        for start in self._static_ranges:
            size = self._static_ranges[start]
            for cpu in range(0, self._last_cpu):
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
            addr: The address to query

        Returns:
            :obj:`bool`: Whether this address belongs to a static range
        """
        for start in self._static_ranges:
            for cpu in range(0, self._last_cpu):
                size = self._static_ranges[start]
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
        size = self._static_ranges[start]
        if addr >= start and addr < start + size:
            return addr - start
        return addr

    def is_module_percpu_var(self, addr: int) -> bool:
        """
        Returns whether the provided value or symbol falls within
        any of the percpu ranges for modules

        Args:
            addr: The address to query

        Returns:
            :obj:`bool`: Whether this address belongs to a module range
        """
        for start in self._module_ranges:
            for cpu in range(0, self.last_cpu):
                size = self._module_ranges[start]
                if addr >= start and addr < start + size:
                    return True
        return False

    @export
    def is_percpu_var(self, var: SymbolOrValue) -> bool:
        """
        Returns whether the provided value or symbol falls within
        any of the percpu ranges

        Args:
            var: The symbol or value to query

        Returns:
            :obj:`bool`: Whether the value belongs to any percpu range
        """
        if isinstance(var, gdb.Symbol):
            var = var.value().address

        var = int(var)
        if self.is_static_percpu_var(var):
            return True
        if self.is_module_percpu_var(var):
            return True
        if self._is_percpu_var_dynamic(var):
            return True
        return False

    def _resolve_percpu_var(self, var):
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
                if var.type != types.void_p_type:
                        var = var.dereference().address
                assert(self.is_percpu_var(var))
            else:
                raise PerCPUError(orig_var)
        # object is a percpu
        elif self.is_percpu_var(var.address):
                var = var.address
        else:
            raise PerCPUError(orig_var)

        return var

    def _get_percpu_var(self, var: SymbolOrValue, cpu: int) -> gdb.Value:
        if cpu < 0:
            raise ValueError("cpu must be >= 0")

        addr = self.__per_cpu_offset[cpu]
        if addr > 0:
            addr += self._relocated_offset(var)

        val = gdb.Value(addr).cast(var.type)
        if var.type != self.void_p_type:
            val = val.dereference()
        return val

    @export
    def get_percpu_var(self, var: SymbolOrValue, cpu: int) -> gdb.Value:
        """
        Retrieve a per-cpu variable for one or all CPUs 

        Args:
            var: The symbol or value to use to resolve the percpu location
            cpu: The cpu for which to return the per-cpu value.

        Returns:
            :obj:`gdb.Value`: The value corresponding to the specified CPU.
            The value is of the same type passed via var.

        Raises:
            :obj:`TypeError`: var is not :obj:`gdb.Symbol` or :obj:`gdb.Value`
            :obj:`.PerCPUError`: var does not fall into any percpu range
            :obj:`ValueError`: cpu is less than ``0``
        """
        var = self._resolve_percpu_var(var)
        return self._get_percpu_var(var, cpu)

    @export
    def get_percpu_vars(self, var: SymbolOrValue,
                        nr_cpus: int=None) -> Dict[int, gdb.Value]:
        """
        Retrieve a per-cpu variable for all CPUs

        Args:
            var: The symbol or value to use to resolve the percpu location
            nr_cpus (optional): The number of CPUs for which to return results
                ``None`` (or unspecified) will use the highest possible
                CPU count.

        Returns:
            :obj:`dict`(:obj:`int`, :obj:`gdb.Value`): The values corresponding
            to every CPU in a dictionary indexed by CPU number.  The type of the
            :obj:`gdb.Value` used as the :obj:`dict` value is the same type as
            the :obj:`gdb.Value` or :obj:`gdb.Symbol` passed as var.

        Raises:
            :obj:`TypeError`: var is not ``gdb.Symbol`` or ``gdb.Value``
            :obj:`.PerCPUError`: var does not fall into any percpu range
            :obj:`ValueError`: nr_cpus is <= ``0``
        """
        if nr_cpus is None:
            nr_cpus = self.last_cpu

        if nr_cpus <= 0:
            raise ValueError("nr_cpus must be > 0")

        vals = dict()

        var = self._resolve_percpu_var(var)
        for cpu in range(0, nr_cpus):
            vals[cpu] = self._get_percpu_var(var, cpu)
        return vals

    @export
    def percpu_counter_sum(self, var: SymbolOrValue) -> int:
        """
        Returns the sum of a percpu counter

        Args:
            var: The percpu counter to sum.  The value must be of type
                ``struct percpu_counter``.

        Returns:
            :obj:`int`: the sum of all components of the percpu counter
        """
        if isinstance(var, gdb.Symbol):
            var = var.value()

        if not (var.type == self.percpu_counter_type or
                (var.type.code == gdb.TYPE_CODE_PTR and
                 var.type.target() == self.percpu_counter_type)):
            raise TypeError("var must be gdb.Symbol or gdb.Value describing `{}' not `{}'"
                                .format(self.percpu_counter_type, var.type))

        total = int(var['count'])

        v = get_percpu_vars(var['counters'])
        for cpu in v:
            total += int(v[cpu])

        return total
