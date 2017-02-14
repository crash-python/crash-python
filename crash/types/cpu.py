#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of, find_member_variant, get_symbol_value
from bitmap import for_each_set_bit

# this wraps no particular type, rather it's a placeholder for
# functions to iterate over online cpu's etc.

# TODO use proper cache namespace?
cpus_online = None

def __get_cpus_mask(sym_mask):
    cpu_mask = get_symbol_value(sym_mask)
    bits = cpu_mask["bits"]
    return list(for_each_set_bit(bits))

def for_each_online_cpu():
    global cpus_online
    if cpus_online is None:
        cpus_online = __get_cpus_mask("cpu_online_mask")
    for cpu in cpus_online:
        yield cpu

