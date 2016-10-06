# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from crash.cache import CrashCache

tasks = {}

def cache_task(task):
    tasks[int(task.task_struct['pid'])] = task

def get_task(pid):
    return tasks[pid]

def drop_task(pid):
    del tasks[pid]
