# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.arch import CrashArchitecture, register, KernelFrameFilter

class Powerpc64Architecture(CrashArchitecture):
    ident = "powerpc:common64"
    aliases = ["ppc64", "elf64-powerpc"]

    def __init__(self):
        super(Powerpc64Architecture, self).__init__()
        self.ulong_type = gdb.lookup_type('unsigned long')
        thread_info_type = gdb.lookup_type('struct thread_info')
        self.thread_info_p_type = thread_info_type.pointer()

        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

    def setup_thread_info(self, thread):
        task = thread.info.task_struct
        thread_info = task['stack'].cast(self.thread_info_p_type)
        thread.info.set_thread_info(thread_info)

    @classmethod
    def get_stack_pointer(cls, thread_struct):
        return thread_struct['ksp']

register(Powerpc64Architecture)
