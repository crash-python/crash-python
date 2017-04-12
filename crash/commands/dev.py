# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import argparse
from crash.commands import CrashCommand, CommandRuntimeError
from crash.types.util import offsetof_type
from crash.types.blockdev import for_each_block_device
from crash.types.classdev import for_each_class_device

import sys

if sys.version_info.major >= 3:
    long = int

class LSDevCommand(CrashCommand):
    """lsdev
"""

    def __init__(self):
        parser = argparse.ArgumentParser(prog="lsdev")
        self.device_type = gdb.lookup_type('struct device')
        super(LSDevCommand, self).__init__('lsdev', parser)

    def execute_dev_stats(self, argv):
        print("MAJOR GENDISK              NAME      REQUEST_QUEUE   TOTAL ASYNC SYNC DRV")
        for blockdev in for_each_block_device("disk"):
            print(blockdev)

    def execute(self, argv):
        sym = gdb.lookup_global_symbol("block_class")

        for dev in for_each_class_device(sym.value()):
            print("{} @ {}".format(dev['kobj']['name'].string(), dev.address))

LSDevCommand()
