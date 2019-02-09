#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.util import container_of, find_member_variant, array_for_each
import crash.types.node
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

class Zones(CrashBaseClass):

    @export
    def for_each_zone(cls):
        for node in crash.types.node,for_each_node():
            for zone in node.for_each_zone():
                yield zone

    @export
    def for_each_populated_zone(cls):
        #TODO: some filter thing?
        for zone in cls.for_each_zone():
            if zone.is_populated():
                yield zone

