# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable, Tuple

from crash.util.symbols import Types
from crash.subsystem.storage import queue_is_mq, rq_is_sync, rq_in_flight
from crash.types.sbitmap import sbitmap_for_each_set
from crash.exceptions import InvalidArgumentError

import gdb

class NoQueueError(RuntimeError):
    pass

types = Types(['struct request', 'struct request_queue',
               'struct sbitmap_queue', 'struct blk_mq_hw_ctx' ])

def _check_queue_type(queue: gdb.Value) -> None:
    if not queue_is_mq(queue):
        raise InvalidArgumentError("Passed request queue is not a multiqueue queue")

def mq_queue_for_each_hw_ctx(queue: gdb.Value) -> Iterable[gdb.Value]:
    """
    Iterates over each ``struct blk_mq_hw_ctx`` in request_queue

    This method iterates over each blk-mq hardware context in request_queue
    and yields each blk_mq_hw_ctx.

    Args:
        queue: The ``struct request_queue`` used to iterate.  The value
            must be of type ``struct request_queue``.

    Yields:
        :obj:`gdb.Value`: Each blk-mq hardware context contained within the
        ``request_queue``. The value is of type ``struct blk_mq_hw_ctx``.
    """
    _check_queue_type(queue)
    for i in range(int(queue['nr_hw_queues'])):
        yield queue['queue_hw_ctx'][i]

def mq_for_each_request_in_queue(queue: gdb.Value, reserved: bool = True) \
                                -> Iterable[gdb.Value]:
    """
    Iterates over each ``struct request`` in request_queue

    This method iterates over the ``request_queue``'s queuelist and
    returns a request for each member.
    This method iterates over the tags of all hardware contexts of
    ``request_queue`` and returns a request for each member.

    Args:
        queue: The ``struct request_queue`` used to iterate.  The value
            must be of type ``struct request_queue``.
        reserved: If true, also reserved requests will be included in the
            iteration

    Yields:
        :obj:`gdb.Value`: Each ``struct request`` contained within the
        ``request_queue``'s queuelist.  The value is of type ``struct request``.
        ``request_queue``'s tags.  The value is of type ``struct request``.
    """
    if int(queue) == 0:
        raise NoQueueError("Queue is NULL")
    _check_queue_type(queue)

    for hctx in mq_queue_for_each_hw_ctx(queue):
        tags = hctx['tags']
        if int(hctx['nr_ctx']) == 0 or int(tags) == 0:
            continue
        if reserved == True and int(tags['nr_reserved_tags']) > 0:
            for tag in sbitmap_for_each_set(tags['breserved_tags']['sb']):
                rq = tags['rqs'][tag]
                if int(rq) != 0 and rq['q'] == queue:
                    yield rq

        for tag in sbitmap_for_each_set(tags['bitmap_tags']['sb']):
            rq = tags['rqs'][tag + int(tags['nr_reserved_tags'])]
            if int(rq) != 0 and rq['q'] == queue:
                yield rq

def mq_requests_in_flight(queue: gdb.Value) -> Tuple[int, int]:
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
    _check_queue_type(queue)
    in_flight = [0, 0]
    for rq in mq_for_each_request_in_queue(queue):
        if rq_in_flight(rq):
            in_flight[rq_is_sync(rq)] += 1

    return (in_flight[0], in_flight[1])

def mq_requests_queued(queue: gdb.Value) -> Tuple[int, int]:
    """
    Report how many requests are queued for this queue

    Args:
        queue: The request queue to inspect for queued requests.
            The value must be of type ``struct request_queue``.

    Returns:
        (:obj:`int`, :obj:`int`): The queued requests.  The first member of
        the 2-tuple is the number of async requests, the second is the number
        of sync requests.
    """
    _check_queue_type(queue)
    queued = [0, 0]
    for rq in mq_for_each_request_in_queue(queue):
        queued[rq_is_sync(rq)] += 1

    return (queued[0], queued[1])
