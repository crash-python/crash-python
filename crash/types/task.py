# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import gdb

from crash.infra import delayed_init

@delayed_init
class LinuxTask(object):
    def __init__(self, task_struct, active=False, cpu=None, regs=None):
        t = gdb.lookup_type('struct task_struct')
        if cpu is not None and not isinstance(cpu, int):
            raise TypeError("cpu must be integer or None")

        if not isinstance(task_struct, gdb.Value) or \
           not task_struct.type != t:
            raise TypeError("task_struct must be gdb.Value describing struct task_struct")

        self.task_struct = task_struct
        self.active = active
        self.cpu = cpu
        self.regs = regs
        self.thread = None
        setattr(LinuxTask, 'task_struct_type', t)

    def attach_thread(self, thread):
        if not isinstance(thread, gdb.InferiorThread):
            raise TypeError("Expected gdb.InferiorThread")
        self.thread = thread
