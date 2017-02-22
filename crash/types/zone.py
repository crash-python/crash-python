#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from .util import container_of, find_member_variant
import crash.types.node
from crash.types.percpu import get_percpu_var
from crash.types.vmstat import VmStat
from .cpu import for_each_online_cpu

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096

zone_type = gdb.lookup_type('struct zone')

def getValue(sym):
    return gdb.lookup_symbol(sym, None)[0].value()

class Zone:

    @staticmethod
    def for_each():
        for node in crash.types.node.Node.for_each_node():
            for zone in node.for_each_zone():
                yield zone

    @staticmethod
    def for_each_populated():
        #TODO: some filter thing?
        for zone in Zone.for_each():
            if zone.is_populated():
                yield zone

    def __init__(self, obj, zid):
        self.gdb_obj = obj
        self.zid = zid

    def is_populated(self):
        if self.gdb_obj["present_pages"] != 0:
            return True
        else:
            return False

    def get_vmstat(self):
        stats = [0] * VmStat.nr_stat_items
        vm_stat = self.gdb_obj["vm_stat"]

        for item in range (0, VmStat.nr_stat_items):
            # TODO abstract atomic?
            stats[item] = int(vm_stat[item]["counter"])
        return stats

    def add_vmstat_diffs(self, diffs):
        for cpu in for_each_online_cpu():
            pageset = get_percpu_var(self.gdb_obj["pageset"], cpu)
            vmdiff = pageset["vm_stat_diff"]
            for item in range (0, VmStat.nr_stat_items):
                diffs[item] += int(vmdiff[item])

    def get_vmstat_diffs(self):
        diffs = [0] * VmStat.nr_stat_items
        self.add_vmstat_diffs(diffs)
        return diffs

