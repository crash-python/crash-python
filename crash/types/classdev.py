# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.types.klist import klist_for_each_entry
from crash.util.symbols import Types

types = Types(['struct device'])

def for_each_class_device(class_struct, subtype=None):
    klist = class_struct['p']['klist_devices']
    for dev in klist_for_each_entry(klist, types.device_type, 'knode_class'):
        if subtype is None or int(subtype) == int(dev['type']):
            yield dev
