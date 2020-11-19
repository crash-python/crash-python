# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.arch import CrashArchitecture, KernelFrameFilter, register_arch
from crash.arch import FetchRegistersCallback

class FR_Placeholder(FetchRegistersCallback): # pylint: disable=abstract-method
    pass

class Powerpc64Architecture(CrashArchitecture):
    ident = "powerpc:common64"
    aliases = ["ppc64", "elf64-powerpc"]

    _fetch_registers = FR_Placeholder

    def __init__(self) -> None:
        super(Powerpc64Architecture, self).__init__()
        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

    def setup_thread_info(self, thread: gdb.InferiorThread) -> None:
        task = thread.info.task_struct
        thread.info.set_thread_info(task['thread_info'].address)

    @classmethod
    def get_stack_pointer(cls, thread_struct: gdb.Value) -> int:
        return int(thread_struct['ksp'])

register_arch(Powerpc64Architecture)
