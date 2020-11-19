#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import List

import gdb

from crash.util import array_for_each
from crash.util.symbols import Types
from crash.types.percpu import get_percpu_var
from crash.types.vmstat import VmStat
from crash.types.cpu import for_each_online_cpu
from crash.types.list import list_for_each_entry
import crash.types.page

class Zone:

    types = Types(['struct page'])

    def __init__(self, obj: gdb.Value, zid: int) -> None:
        self.gdb_obj = obj
        self.zid = zid
        self.nid = int(obj["node"])

    def is_populated(self) -> bool:
        return self.gdb_obj["present_pages"] != 0

    def get_vmstat(self) -> List[int]:
        stats = [0] * VmStat.nr_stat_items
        vm_stat = self.gdb_obj["vm_stat"]

        for item in range(0, VmStat.nr_stat_items):
            # TODO abstract atomic?
            stats[item] = int(vm_stat[item]["counter"])
        return stats

    def add_vmstat_diffs(self, diffs: List[int]) -> None:
        for cpu in for_each_online_cpu():
            pageset = get_percpu_var(self.gdb_obj["pageset"], cpu)
            vmdiff = pageset["vm_stat_diff"]
            for item in range(0, VmStat.nr_stat_items):
                diffs[item] += int(vmdiff[item])

    def get_vmstat_diffs(self) -> List[int]:
        diffs = [0] * VmStat.nr_stat_items
        self.add_vmstat_diffs(diffs)
        return diffs

    def _check_free_area(self, area: gdb.Value, is_pcp: bool) -> None:
        nr_free = 0
        if is_pcp:
            list_array_name = "lists"
            error_desc = "pcplist"
        else:
            list_array_name = "free_list"
            error_desc = "free area"
        for free_list in array_for_each(area[list_array_name]):
            try:
                for page_obj in list_for_each_entry(free_list,
                                                    self.types.page_type,
                                                    "lru"):
                    page = crash.types.page.Page.from_obj(page_obj)
                    nr_free += 1
                    if page.get_nid() != self.nid or page.get_zid() != self.zid:
                        print(f"page 0x{int(page_obj.address):x} misplaced on "
                              f"{error_desc} of node {self.nid} zone {self.zid}, "
                              f"has flags for node {page.get_nid()} zone {page.get_zid()}")
            except BufferError as e:
                print(f"Error traversing free area: {e}")
        nr_expected = area["count"] if is_pcp else area["nr_free"]
        if nr_free != nr_expected:
            print(f"nr_free mismatch in {error_desc} 0x{int(area.address):x}: "
                  f"expected {nr_expected}, counted {nr_free}")

    def check_free_pages(self) -> None:
        for area in array_for_each(self.gdb_obj["free_area"]):
            self._check_free_area(area, False)
        for cpu in for_each_online_cpu():
            pageset = get_percpu_var(self.gdb_obj["pageset"], cpu)
            self._check_free_area(pageset["pcp"], True)
