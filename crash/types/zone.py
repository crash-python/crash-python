#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from util import container_of, find_member_variant
import crash.types.node
from crash.types.percpu import get_percpu_var

# TODO: un-hardcode this
VMEMMAP_START   = 0xffffea0000000000
DIRECTMAP_START = 0xffff880000000000
PAGE_SIZE       = 4096L

# TODO abstract away
nr_cpu_ids = long(gdb.lookup_global_symbol("nr_cpu_ids").value())
nr_node_ids = long(gdb.lookup_global_symbol("nr_node_ids").value())

zone_type = gdb.lookup_type('struct zone')

def getValue(sym):
    return gdb.lookup_symbol(sym, None)[0].value()

nr_stat_items = int(getValue("NR_VM_ZONE_STAT_ITEMS"))

class Zone:

    @staticmethod
    def for_each():
        for node in crash.types.node.Node.for_each_node():
            for zone in node.for_each_zone():
                yield zone

    def __init__(self, obj):
        self.gdb_obj = obj

    def get_vmstat(self):
        stats = [0L] * nr_stat_items
        vm_stat = self.gdb_obj["vm_stat"]

        for item in range (0, nr_stat_items):
            # TODO abstract atomic?
            stats[item] = long(vm_stat[item]["counter"])
        return stats

    def add_vmstat_diffs(self, diffs):
        pagesets = get_percpu_var(self.gdb_obj["pageset"])

        for cpu, pageset in pagesets.iteritems():
            vmdiff = pageset["vm_stat_diff"]
            for item in range (0, nr_stat_items):
                diffs[item] += int(vmdiff[item])

    def get_vmstat_diffs(self):
        diffs = [0L] * nr_stat_items
        self.add_vmstat_diffs(diffs)
        return diffs

