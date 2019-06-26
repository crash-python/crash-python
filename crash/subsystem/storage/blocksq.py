# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable, Tuple

from crash.util.symbols import Types
from crash.types.list import list_for_each_entry
from crash.subsystem.storage import queue_is_mq
from crash.exceptions import InvalidArgumentError

import gdb

class NoQueueError(RuntimeError):
    pass

types = Types(['struct request'])

def _check_queue_type(queue: gdb.Value) -> None:
    if queue_is_mq(queue):
        raise InvalidArgumentError("Passed request queue is a multiqueue queue")

def sq_for_each_request_in_queue(queue: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterates over each ``struct request`` in request_queue

    This method iterates over the ``request_queue``'s queuelist and
    returns a request for each member.

    Args:
        queue: The ``struct request_queue`` used to iterate.  The value
            must be of type ``struct request_queue``.

    Yields:
        :obj:`gdb.Value`: Each ``struct request`` contained within the
        ``request_queue``'s queuelist.  The value is of type ``struct request``.
    """
    if int(queue) == 0:
        raise NoQueueError("Queue is NULL")
    _check_queue_type(queue)
    return list_for_each_entry(queue['queue_head'], types.request_type,
                               'queuelist')

def sq_requests_in_flight(queue: gdb.Value) -> Tuple[int, int]:
    """
    Report how many requests are in flight for this queue

    Args:
        queue: The request queue to inspect for requests in flight.
            The value must be of type ``struct request_queue``.

    Returns:
        (:obj:`int`, :obj:`int`): The requests in flight.  The first member of
        the 2-tuple is the number of read requests, the second is the number
        of write requests.
    """
    _check_queue_type(queue)
    return (int(queue['in_flight'][0]),
            int(queue['in_flight'][1]))
