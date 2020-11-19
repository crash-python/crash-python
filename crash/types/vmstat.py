#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import List, Tuple

import gdb

from crash.util.symbols import Types, TypeCallbacks, Symbols
from crash.types.percpu import get_percpu_var
from crash.types.cpu import for_each_online_cpu

class VmStat:
    types = Types(['enum zone_stat_item', 'enum vm_event_item'])
    symbols = Symbols(['vm_event_states'])

    nr_stat_items = -1
    nr_event_items = -1

    vm_stat_names: List[str] = list()
    vm_event_names: List[str] = list()

    @classmethod
    def check_enum_type(cls, gdbtype: gdb.Type) -> None:
        if gdbtype == cls.types.enum_zone_stat_item_type:
            (items, names) = cls.__populate_names(gdbtype,
                                                  'NR_VM_ZONE_STAT_ITEMS')
            cls.nr_stat_items = items
            cls.vm_stat_names = names
        elif gdbtype == cls.types.enum_vm_event_item_type:
            (items, names) = cls.__populate_names(gdbtype,
                                                  'NR_VM_EVENT_ITEMS')
            cls.nr_event_items = items
            cls.vm_event_names = names
        else:
            raise TypeError("Unexpected type {}".format(gdbtype.name))

    @classmethod
    def __populate_names(cls, enum_type: gdb.Type,
                         items_name: str) -> Tuple[int, List[str]]:
        nr_items = enum_type[items_name].enumval

        names = ["__UNKNOWN__"] * nr_items

        for field in enum_type.fields():
            if field.enumval < nr_items:
                names[field.enumval] = field.name

        return (nr_items, names)

    @classmethod
    def get_stat_names(cls) -> List[str]:
        return cls.vm_stat_names

    @classmethod
    def get_event_names(cls) -> List[str]:
        return cls.vm_event_names

    @classmethod
    def get_events(cls) -> List[int]:
        nr = cls.nr_event_items
        events = [0] * nr

        for cpu in for_each_online_cpu():
            states = get_percpu_var(cls.symbols.vm_event_states, cpu)
            for item in range(0, nr):
                events[item] += int(states["event"][item])

        return events

type_cbs = TypeCallbacks([('enum zone_stat_item', VmStat.check_enum_type),
                          ('enum vm_event_item', VmStat.check_enum_type)])
