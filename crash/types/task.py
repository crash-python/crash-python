#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

task_struct_type = gdb.lookup_type('struct task_struct')

class LinuxTask:
    def __init__(self, task_struct, active = False,
                 cpu = None, regs = None):
        if cpu is not None and not isinstance(cpu, int):
            raise TypeError("cpu must be integer or None")

        if not isinstance(task_struct, gdb.Value) or \
           not task_struct.type != task_struct_type:
            raise TypeError("task_struct must be gdb.Value describing struct task_struct")

        self.task_struct = task_struct
        self.active = active
        self.cpu = cpu
        self.regs = regs

    def attach_thread(self, thread):
        if not isinstance(thread, gdb.InferiorThread):
            raise TypeError("Expected gdb.InferiorThread")
        self.thread = thread
