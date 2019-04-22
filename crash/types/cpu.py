#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.util import container_of, find_member_variant, get_symbol_value
from crash.types.bitmap import for_each_set_bit

# this wraps no particular type, rather it's a placeholder for
# functions to iterate over online cpu's etc.
class TypesCPUClass(CrashBaseClass):

    __symbol_callbacks__ = [ ('cpu_online_mask', 'setup_cpus_mask') ]

    cpus_online = None

    @classmethod
    def setup_cpus_mask(cls, cpu_mask):
        bits = cpu_mask.value()["bits"]
        cls.cpus_online = list(for_each_set_bit(bits))

    @export
    def for_each_online_cpu(self):
        for cpu in self.cpus_online:
            yield cpu

