# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.types.klist import klist_for_each_entry

class ClassDeviceClass(CrashBaseClass):
    __types__ = [ 'struct device' ]

    @export
    def for_each_class_device(self, class_struct, subtype=None):
        klist = class_struct['p']['klist_devices']
        for dev in klist_for_each_entry(klist, self.device_type, 'knode_class'):
            if subtype is None or int(subtype) == int(dev['type']):
                yield dev
