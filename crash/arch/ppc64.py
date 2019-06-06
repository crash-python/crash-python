# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.arch import CrashArchitecture, KernelFrameFilter, register_arch

import gdb

class Powerpc64Architecture(CrashArchitecture):
    ident = "powerpc:common64"
    aliases = ["ppc64", "elf64-powerpc"]

    def __init__(self) -> None:
        super(Powerpc64Architecture, self).__init__()
        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

    def setup_thread_info(self, thread: gdb.InferiorThread) -> None:
        task = thread.info.task_struct
        thread.info.set_thread_info(task['thread_info'].address)

    @classmethod
    def get_stack_pointer(cls, thread_struct: gdb.Value) -> gdb.Value:
        return thread_struct['ksp']

    def fetch_register_active(self, thread: gdb.InferiorThread,
                              register: int) -> None:
        raise NotImplementedError("ppc64 support does not cover threads yet")

    def fetch_register_scheduled(self, thread: gdb.InferiorThread,
                                 register: gdb.Register) -> None:
        raise NotImplementedError("ppc64 support does not cover threads yet")

register_arch(Powerpc64Architecture)
