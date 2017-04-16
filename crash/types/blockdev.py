# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
from crash.infra import exporter, export, delayed_init
from crash.types.classdev import for_each_class_device
from crash.util import container_of

if sys.version_info.major >= 3:
    long = int

@exporter
@delayed_init
class BlockDeviceClass(object):
    def __init__(self):
        self.block_class = gdb.lookup_global_symbol("block_class").value()
        self.gendisk_type = gdb.lookup_type('struct gendisk')

    @export
    def for_each_block_device(self, subtype=None):
        for dev in for_each_class_device(self.block_class, subtype):
            yield container_of(dev, self.gendisk_type, 'part0.__dev')

    @export
    @staticmethod
    def gendisk_name(gendisk):
        return gendisk['disk_name'].string()

    @export
    def block_device_name(self, bdev):
        return self.gendisk_name(bdev['bd_disk'])
