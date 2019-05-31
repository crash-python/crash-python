#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.util import array_for_each
from crash.util.symbols import Types
from crash.types.percpu import get_percpu_var
from crash.types.vmstat import VmStat
from crash.types.cpu import for_each_online_cpu
from crash.types.list import list_for_each_entry
import crash.types.page

class Zone(object):

    types = Types(['struct page'])

    def __init__(self, obj, zid):
        self.gdb_obj = obj
        self.zid = zid
        self.nid = int(obj["node"])

    def is_populated(self):
        if self.gdb_obj["present_pages"] != 0:
            return True
        else:
            return False

    def get_vmstat(self):
        stats = [0] * VmStat.nr_stat_items
        vm_stat = self.gdb_obj["vm_stat"]

        for item in range(0, VmStat.nr_stat_items):
            # TODO abstract atomic?
            stats[item] = int(vm_stat[item]["counter"])
        return stats

    def add_vmstat_diffs(self, diffs):
        for cpu in for_each_online_cpu():
            pageset = get_percpu_var(self.gdb_obj["pageset"], cpu)
            vmdiff = pageset["vm_stat_diff"]
            for item in range(0, VmStat.nr_stat_items):
                diffs[item] += int(vmdiff[item])

    def get_vmstat_diffs(self):
        diffs = [0] * VmStat.nr_stat_items
        self.add_vmstat_diffs(diffs)
        return diffs

    def _check_free_area(self, area, is_pcp):
        nr_free = 0
        list_array_name = "lists" if is_pcp else "free_list"
        for free_list in array_for_each(area[list_array_name]):
            for page_obj in list_for_each_entry(free_list,
                                                self.types.page_type,
                                                "lru"):
                page = crash.types.page.Page.from_obj(page_obj)
                nr_free += 1
                if page.get_nid() != self.nid or page.get_zid() != self.zid:
                    print("page {:#x} misplaced on {} of zone {}:{}, has flags for zone {}:{}".
                          format(int(page_obj.address), "pcplist" if is_pcp else "freelist",
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
