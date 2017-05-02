# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
from crash.infra import delayed_init, CrashBaseClass, export
from crash.types.klist import klist_for_each_entry

if sys.version_info.major >= 3:
    long = int

@delayed_init
class ClassDeviceClass(CrashBaseClass):
    def __init__(self):
        self.device_type = gdb.lookup_type('struct device')

    @export
    def for_each_class_device(self, class_struct, subtype=None):
        klist = class_struct['p']['klist_devices']
        for dev in klist_for_each_entry(klist, self.device_type, 'knode_class'):
            if subtype is None or long(subtype) == long(dev['type']):
                yield dev
