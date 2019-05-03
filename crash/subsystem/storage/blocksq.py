# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.util.symbols import Types
from crash.types.list import list_for_each_entry
from crash.cache.syscache import kernel

class NoQueueError(RuntimeError):
    pass

types = Types([ 'struct request' ])

def for_each_request_in_queue(queue):
    """
    Iterates over each struct request in request_queue

    This method iterates over the request_queue's queuelist and
    returns a request for each member.

    Args:
        queue(gdb.Value<struct request_queue>): The struct request_queue
            used to iterate

    Yields:
        gdb.Value<struct request>: Each struct request contained within
           the request_queue's queuelist
    """
    if int(queue) == 0:
        raise NoQueueError("Queue is NULL")
    return list_for_each_entry(queue['queue_head'], types.request_type,
                               'queuelist')

def request_age_ms(request):
    """
    Returns the age of the request in milliseconds

    This method returns the difference between the current time
    (jiffies) and the request's start_time, in milliseconds.

    Args:
        request(gdb.Value<struct request>): The struct request used
            to determine age

    Returns:
        int: Difference between the request's start_time and
            current jiffies in milliseconds.
    """
    return kernel.jiffies_to_msec(kernel.jiffies - request['start_time'])
