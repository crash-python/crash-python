#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.util import container_of, find_member_variant, array_for_each
import crash.types.node
from crash.types.percpu import get_percpu_var
from crash.types.vmstat import VmStat
from cpu import for_each_online_cpu
from crash.types.list import list_for_each_entry

def getValue(sym):
    return gdb.lookup_symbol(sym, None)[0].value()

class Zone(CrashBaseClass):
    __types__ = [ 'struct zone', 'struct page' ]

    def __init__(self, obj, zid):
        self.gdb_obj = obj
        self.zid = zid
        self.nid = long(obj["node"])

    def is_populated(self):
        if self.gdb_obj["present_pages"] != 0:
            return True
        else:
            return False

    def get_vmstat(self):
        stats = [0L] * VmStat.nr_stat_items
        vm_stat = self.gdb_obj["vm_stat"]

        for item in range (0, VmStat.nr_stat_items):
            # TODO abstract atomic?
            stats[item] = long(vm_stat[item]["counter"])
        return stats

    def add_vmstat_diffs(self, diffs):
        for cpu in for_each_online_cpu():
            pageset = get_percpu_var(self.gdb_obj["pageset"], cpu)
            vmdiff = pageset["vm_stat_diff"]
            for item in range (0, VmStat.nr_stat_items):
                diffs[item] += int(vmdiff[item])

    def get_vmstat_diffs(self):
        diffs = [0L] * VmStat.nr_stat_items
        self.add_vmstat_diffs(diffs)
        return diffs

    def _check_free_area(self, area, is_pcp):
        nr_free = 0
        list_array_name = "lists" if is_pcp else "free_list"
        for free_list in array_for_each(area[list_array_name]):
            for page_obj in list_for_each_entry(free_list, self.page_type, "lru"):
                page = crash.types.page.Page.from_obj(page_obj)
                nr_free += 1
                if page.get_nid() != self.nid or page.get_zid() != self.zid:
                    print("page {:#x} misplaced on {} of zone {}:{}, has flags for zone {}:{}".
                        format(long(page_obj.address), "pcplist" if is_pcp else "freelist",
                                self.nid, self.zid, page.get_nid(), page.get_zid()))
        nr_expected = area["count"] if is_pcp else area["nr_free"]
        if nr_free != nr_expected:
            print("nr_free mismatch in {} {}: expected {}, counted {}".
                format("pcplist" if is_pcp else "area", area.address,
                        nr_expected, nr_free))

    def check_free_pages(self):
        for area in array_for_each(self.gdb_obj["free_area"]):
            self._check_free_area(area, False)
        for cpu in for_each_online_cpu():
            pageset = get_percpu_var(self.gdb_obj["pageset"], cpu)
            self._check_free_area(pageset["pcp"], True)

class Zones(CrashBaseClass):

    @export
    def for_each_zone(cls):
        for node in crash.types.node.for_each_node():
            for zone in node.for_each_zone():
                yield zone

    @export
    def for_each_populated_zone(cls):
        #TODO: some filter thing?
        for zone in cls.for_each_zone():
            if zone.is_populated():
                yield zone

