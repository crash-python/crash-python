# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gdb
import sys

if sys.version_info.major >= 3:
    long = int

from crash.infra import CrashBaseClass, export
from crash.types.list import list_for_each_entry
from crash.cache.syscache import kernel

class NoQueueError(RuntimeError):
    pass

class SingleQueueBlock(CrashBaseClass):
    __types__ = [ 'struct request' ]

    @export
    def for_each_request_in_queue(self, queue):
        if long(queue) == 0:
            raise NoQueueError("Queue is NULL")
        return list_for_each_entry(queue['queue_head'], self.request_type,
                                   'queuelist')

    @export
    @classmethod
    def request_age_ms(cls, request):
        return kernel.jiffies_to_msec(kernel.jiffies - request['start_time'])
