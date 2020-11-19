# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable, Tuple

import gdb

from crash.util.symbols import Types
from crash.subsystem.storage import queue_is_mq
from crash.subsystem.storage.blocksq import sq_for_each_request_in_queue, \
    sq_requests_in_flight, sq_requests_queued
from crash.subsystem.storage.blockmq import mq_for_each_request_in_queue, \
    mq_requests_in_flight, mq_requests_queued, mq_queue_request_stats

def requests_in_flight(queue: gdb.Value) -> Tuple[int, int]:
    """
    Report how many requests are in flight for this queue

    Args:
        queue: The request queue to inspect for requests in flight.
            The value must be of type ``struct request_queue``.

    Returns:
        (:obj:`int`, :obj:`int`): The requests in flight.  The first member of
        the 2-tuple is the number of async requests, the second is the number
        of sync requests.
    """
    if queue_is_mq(queue):
       return mq_requests_in_flight(queue)
    return sq_requests_in_flight(queue)

def requests_queued(queue: gdb.Value) -> Tuple[int, int]:
    """
    Report how many requests are queued for this queue

    Args:
        queue: The request queue to inspect for number of queued requests.
            The value must be of type ``struct request_queue``.

    Returns:
        (:obj:`int`, :obj:`int`): The number of queued requests.  The first
        member of the 2-tuple is the number of async requests, the second is
        the number of sync requests.
    """
    if queue_is_mq(queue):
       return mq_requests_queued(queue)
    return sq_requests_queued(queue)

def for_each_request_in_queue(queue: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterates over each ``struct request`` in request_queue

    This method iterates over requests queued in ``request_queue``. It takes
    care of properly handling both single and multiqueue queues.

    Args:
        queue: The ``struct request_queue`` used to iterate.  The value
            must be of type ``struct request_queue``.

    Yields:
        :obj:`gdb.Value`: Each ``struct request`` contained within the
        ``request_queue``.  The value is of type ``struct request``.
    """
    if queue_is_mq(queue):
        return mq_for_each_request_in_queue(queue)
    return sq_for_each_request_in_queue(queue)

def queue_request_stats(queue: gdb.Value) -> Tuple[int, int, int, int]:
    """
    Report various request information for this queue

    Args:
        queue: The request queue to inspect for request information.
            The value must be of type ``struct request_queue``.

    Returns:
        (:obj:`int`, :obj:`int`, :obj:`int`, :obj:`int`): Number queued async
        requests, number of queued sync requests, number of async requests
        being processed by the driver, number of sync requests being processed
        by the driver.
    """
    if queue_is_mq(queue):
        return mq_queue_request_stats(queue)
    return sq_requests_queued(queue) + sq_requests_in_flight(queue) # type: ignore
