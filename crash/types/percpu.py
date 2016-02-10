#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

ulong = gdb.lookup_type('unsigned long')
charp = gdb.lookup_type('char').pointer()

per_cpu_offset_sym = gdb.lookup_global_symbol('__per_cpu_offset')
per_cpu_offset = long(per_cpu_offset_sym.value().address)
offset_type = per_cpu_offset_sym.value()[0].type
nr_cpus = per_cpu_offset_sym.type.sizeof / offset_type.sizeof

def is_percpu_symbol(sym):
    return sym.section is not None and 'percpu' in sym.section

def get_percpu_var_nocheck(sym, cpu=None):
    symtype = sym.type
    if cpu is None:
        vals = {}
        for cpu in range(0, nr_cpus):
            vals[cpu] = get_percpu_var_nocheck(sym, cpu)
        return vals

    addr  = per_cpu_offset_sym.value()[cpu]
    addr += sym.value().address.cast(charp)
    return addr.cast(symtype.pointer()).dereference()

def get_percpu_var(sym, cpu=None):
    if not is_percpu_symbol(sym):
        raise TypeError("symbol not in percpu section")

    return get_percpu_var_nocheck(sym, cpu)
