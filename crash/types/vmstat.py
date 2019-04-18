#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.util import container_of, find_member_variant
import crash.types.node
from crash.types.percpu import get_percpu_var
from cpu import for_each_online_cpu

class VmStat(CrashBaseClass):
    __types__ = ['enum zone_stat_item', 'enum vm_event_item']
    __type_callbacks__ = [ ('enum zone_stat_item', 'check_enum_type'),
                           ('enum vm_event_item', 'check_enum_type') ]

    nr_stat_items = None
    nr_event_items = None
    
    vm_stat_names = None
    vm_event_names = None

    @classmethod
    def check_enum_type(cls, gdbtype):
        if gdbtype == cls.enum_zone_stat_item_type:
            (items, names) = cls.__populate_names(gdbtype, 'NR_VM_ZONE_STAT_ITEMS')
            cls.nr_stat_items = items
            cls.vm_stat_names = names
        elif gdbtype == cls.enum_vm_event_item_type:
            (items, names) = cls.__populate_names(gdbtype, 'NR_VM_EVENT_ITEMS')
            cls.nr_event_items = items
            cls.vm_event_names = names
        else:
            raise TypeError("Unexpected type {}".format(gdbtype.name))

    @classmethod
    def __populate_names(cls, enum_type, items_name):
            nr_items = enum_type[items_name].enumval

            names = ["__UNKNOWN__"] * nr_items

            for field in enum_type.fields():
                if field.enumval < nr_items:
                    names[field.enumval] = field.name 
            
            return (nr_items, names)

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

        for cpu in for_each_online_cpu():
            states = get_percpu_var(states_sym, cpu)
            for item in range(0, nr):
                events[item] += long(states["event"][item])

        return events

