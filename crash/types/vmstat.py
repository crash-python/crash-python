#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of, find_member_variant
import crash.types.node
from crash.types.percpu import get_percpu_var, get_percpu_var_nocheck

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096L

# TODO abstract away
nr_cpu_ids = long(gdb.lookup_global_symbol("nr_cpu_ids").value())
nr_node_ids = long(gdb.lookup_global_symbol("nr_node_ids").value())

def getValue(sym):
    return gdb.lookup_symbol(sym, None)[0].value()

class VmStat:

    nr_stat_items = int(getValue("NR_VM_ZONE_STAT_ITEMS"))
    nr_event_items = int(getValue("NR_VM_EVENT_ITEMS"))
    
    vm_stat_names = None
    vm_event_names = None

    @staticmethod
    def __populate_names(nr_items, enum_name):
            names = ["__UNKNOWN__"] * nr_items

            enum = gdb.lookup_type(enum_name)
            for field in enum.fields():
                if field.enumval < nr_items:
                    names[field.enumval] = field.name 
            
            return names

    @staticmethod
    def get_stat_names():
        if VmStat.vm_stat_names is None:
            VmStat.vm_stat_names = VmStat.__populate_names(
                    VmStat.nr_stat_items, "enum zone_stat_item")
        return VmStat.vm_stat_names

    @staticmethod
    def get_event_names():
        if VmStat.vm_event_names is None:
            VmStat.vm_event_names = VmStat.__populate_names(
                    VmStat.nr_event_items, "enum vm_event_item")
        return VmStat.vm_event_names

    @staticmethod
    def get_events():
        states_sym = gdb.lookup_global_symbol("vm_event_states")
        nr = VmStat.nr_event_items
        events = [0L] * nr

        for cpu in range(0, nr_cpu_ids):
            states = get_percpu_var_nocheck(states_sym, cpu)
            for item in range(0, nr):
                events[item] += long(states["event"][item])

        return events

