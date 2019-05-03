#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.types.bitmap import for_each_set_bit
from crash.exceptions import DelayedAttributeError

from typing import List, Iterable

# this wraps no particular type, rather it's a placeholder for
# functions to iterate over online cpu's etc.
class TypesCPUClass(CrashBaseClass):
    __symbol_callbacks__ = [ ('cpu_online_mask', '_setup_online_mask'),
                             ('__cpu_online_mask', '_setup_online_mask'),
                             ('cpu_possible_mask', '_setup_possible_mask'),
                             ('__cpu_possible_mask', '_setup_possible_mask') ]

    cpus_online: List[int] = list()
    cpus_possible: List[int] = list()

    @classmethod
    def _setup_online_mask(cls, symbol: gdb.Symbol) -> None:
        cls.cpu_online_mask = symbol.value()
        bits = cls.cpu_online_mask["bits"]
        cls.cpus_online = list(for_each_set_bit(bits))

    @export
    def for_each_online_cpu(self) -> Iterable[int]:
        """
        Yield CPU numbers of all online CPUs

        Yields:
            int: Number of a possible CPU location
        """
        for cpu in self.cpus_online:
            yield cpu

    @export
    def highest_online_cpu_nr(self) -> None:
        """
        Return The highest online CPU number

        Returns:
            int: The highest online CPU number
        """
        if not TypesCPUClass.cpus_online :
            raise DelayedAttributeError('cpus_online')
        return self.cpus_online[-1]

    @classmethod
    def _setup_possible_mask(cls, cpu_mask: gdb.Symbol) -> None:
        cls.cpu_possible_mask = cpu_mask.value()
        bits = cls.cpu_possible_mask["bits"]
        cls.cpus_possible = list(for_each_set_bit(bits))

    @export
    def for_each_possible_cpu(self) -> Iterable[int]:
        """
        Yield CPU numbers of all possible CPUs

        Yields:
            int: Number of a possible CPU location
        """
        for cpu in self.cpus_possible:
            yield cpu

    @export
    def highest_possible_cpu_nr(self) -> int:
        """
        Return The highest possible CPU number

        Returns:
            int: The highest possible CPU number
        """
        if not self.cpus_possible:
            raise DelayedAttributeError('cpus_possible')
        return self.cpus_possible[-1]
