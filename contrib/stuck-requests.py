#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
# bsc#1031358

# This script dumps stuck requests for every disk on the system

from crash.subsystem.storage import for_each_disk
from crash.subsystem.storage import for_each_bio_in_stack
from crash.subsystem.storage import gendisk_name
from crash.subsystem.storage.blocksq import for_each_request_in_queue
from crash.types.list import list_for_each_entry
from crash.util import get_symbol_value
from crash.cache.syscache import kernel, jiffies_to_msec

empty = []

flush_end_io = get_symbol_value('flush_end_io')

for b in for_each_disk():
    name = gendisk_name(b)
    count = 0
    for r in for_each_request_in_queue(b['queue']):
        age_in_jiffies = kernel.jiffies - r['start_time']
        age = float(long(kernel.jiffies_to_msec(age_in_jiffies))) / 1000
        if count == 0:
            print name
        if r['bio']:
            print "{}: {:x} request: age={}s, bio chain".format(
                    count, long(r.address), age, long(r['bio']))
            n=0
            for entry in for_each_bio_in_stack(r['bio']):
                print "  {}: {}".format(n, entry['description'])
                n += 1
        else:
            if r['end_io'] == flush_end_io:
                print "{}: {:x} request: age={}s, pending flush request".format(
                        count, long(r.address), age)
            else:
                print "{}: {:x} request: start={}, undecoded".format(
                        count, long(r.address), age)
        count += 1
        print

    if count == 0:
        empty.append(name)

#print "Queues for the following devices were empty: {}".format(", ".join(empty))
