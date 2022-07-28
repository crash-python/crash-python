# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Optional

import gdb

import crash.target
from crash.target import register_target
from crash.target import KernelFrameFilter

class _FetchRegistersBase(crash.target.TargetFetchRegistersBase):
    def __init__(self) -> None:
        super().__init__()
        self.filter: KernelFrameFilter

    def fetch_active(self, thread: gdb.InferiorThread,
                     register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        registers = {}
        task = thread.info
        for reg in task.regs:
            if (reg == "pc" and register is not None and
                    register.name != "pc"):
                continue
            try:
                registers[reg] = task.regs[reg]
            except KeyError:
                pass

        return registers

    def fetch_scheduled(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        registers: gdb.RegisterCollectionType = {}
        return registers

# pylint: disable=abstract-method
class PPC64TargetBase(crash.target.TargetBase):
    ident = "powerpc:common64"
    aliases = ["ppc64", "elf64-powerpc"]

    def __init__(self) -> None:
        super().__init__()

        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

    def arch_setup_thread(self, thread: gdb.InferiorThread) -> None:
        task = thread.info.task_struct
        thread.info.set_thread_info(task['thread_info'].address)
        thread.info.set_thread_struct(task['thread'])

    def get_stack_pointer(self, thread: gdb.InferiorThread) -> int:
        return int(thread.info.thread_struct['ksp'])

class PPC64Target(_FetchRegistersBase, PPC64TargetBase):
    pass

register_target(PPC64Target)
