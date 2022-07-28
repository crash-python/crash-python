# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Optional
import re

import gdb
import crash.target
from crash.target import IncorrectTargetError, register_target
from crash.target import KernelFrameFilter
from crash.util.symbols import Types, MinimalSymvals
from crash.util.symbols import TypeCallbacks, MinimalSymbolCallbacks

types = Types(['struct inactive_task_frame *', 'struct thread_info *',
               'unsigned long *'])
msymvals = MinimalSymvals(['thread_return'])

# pylint: disable=abstract-method
class _FetchRegistersBase(crash.target.TargetFetchRegistersBase):
    def __init__(self) -> None:
        super().__init__()
        self.filter: KernelFrameFilter

    def fetch_active(self, thread: gdb.InferiorThread,
                     register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        regmap = {
            "rflags" : "eflags"
        }
        registers = {}
        task = thread.info
        for reg in task.regs:
            if (reg == "rip" and register is not None and
                    register.name != "rip"):
                continue
            try:
                # vmcore uses rflags, gdb uses eflags
                if reg in regmap:
                    reg = regmap[reg]
                registers[reg] = task.regs[reg]
            except KeyError:
                pass

        return registers

class _FetchRegistersInactiveFrame(_FetchRegistersBase):
    def __init__(self) -> None:
        super().__init__()

        self._scheduled_rip: int = 0
        if not self._enabled:
            raise IncorrectTargetError("Missing struct inactive_task_frame type")

    # We don't have CFI for __switch_to_asm but we do know what it looks like.
    # We push 6 registers and then swap rsp, so we can just rewind back
    # to __switch_to_asm getting called and then populate the registers that
    # were saved on the stack.
    def find_scheduled_rip(self, task: gdb.Value) -> None:
        top = int(task['stack']) + 16*1024
        callq = re.compile(r"callq?.*<(\w+)>")

        rsp = task['thread']['sp'].cast(types.unsigned_long_p_type)

        count = 0
        while int(rsp) < top:
            val = int(rsp.dereference()) - 5
            if val > self.filter.address:
                try:
                    insn = gdb.execute(f"x/i {val:#x}", to_string=True)
                except gdb.error:
                    insn = None

                if insn:
                    m = callq.search(insn)
                    if m and m.group(1) == "__switch_to_asm":
                        print("Set scheduled RIP")
                        self._scheduled_rip = val
                        return

            rsp += 1
            count += 1

        raise RuntimeError("Cannot locate stack frame offset for __schedule")

    def get_scheduled_rip(self, task: gdb.Value) -> int:
        if self._scheduled_rip == 0:
            self.find_scheduled_rip(task)

        return self._scheduled_rip

    def fetch_scheduled(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        registers: gdb.RegisterCollectionType = {}
        task = thread.info.task_struct

        rsp = task['thread']['sp'].cast(types.unsigned_long_p_type)
        registers['rsp'] = rsp

        frame = rsp.cast(types.inactive_task_frame_p_type).dereference()

        registers['rip'] = self.get_scheduled_rip(task)
        registers['rbp'] = frame['bp']
        registers['rbx'] = frame['bx']
        registers['r12'] = frame['r12']
        registers['r13'] = frame['r13']
        registers['r14'] = frame['r14']
        registers['r15'] = frame['r15']
        registers['cs'] = 2*8
        registers['ss'] = 3*8

        thread.info.stack_pointer = rsp
        thread.info.valid_stack = True

        return registers

class _FetchRegistersThreadReturn(_FetchRegistersBase):
    def fetch_scheduled(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        registers: gdb.RegisterCollectionType = {}
        task = thread.info.task_struct

        rsp = task['thread']['sp'].cast(types.unsigned_long_p_type)
        rbp = rsp.dereference().cast(types.unsigned_long_p_type)
        rbx = (rbp - 1).dereference()
        r12 = (rbp - 2).dereference()
        r13 = (rbp - 3).dereference()
        r14 = (rbp - 4).dereference()
        r15 = (rbp - 5).dereference()

        # The two pushes that don't have CFI info
        # rsp += 2

        # ex = in_exception_stack(rsp)
        # if ex:
        #     print("EXCEPTION STACK: pid {:d}".format(task['pid']))

        registers['rip'] = msymvals.thread_return
        registers['rsp'] = rsp
        registers['rbp'] = rbp
        registers['rbx'] = rbx
        registers['r12'] = r12
        registers['r13'] = r13
        registers['r14'] = r14
        registers['r15'] = r15
        registers['cs'] = 2*8
        registers['ss'] = 3*8

        thread.info.stack_pointer = rsp
        thread.info.valid_stack = True

        return registers

class X8664TargetBase(crash.target.TargetBase):
    ident = "i386:x86-64"
    aliases = ["x86_64"]

    def __init__(self) -> None:
        super().__init__()

        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

    def arch_setup_thread(self, thread: gdb.InferiorThread) -> None:
        task = thread.info.task_struct
        thread_info = task['stack'].cast(types.thread_info_p_type)
        thread.info.set_thread_info(thread_info)
        thread.info.set_thread_struct(task['thread'])

    def get_stack_pointer(self, thread: gdb.InferiorThread) -> int:
        return int(thread.info.thread_struct['sp'])

class X8664ThreadReturnTarget(_FetchRegistersThreadReturn, X8664TargetBase):
    pass

class X8664InactiveFrameTarget(_FetchRegistersInactiveFrame, X8664TargetBase):
    pass

type_cbs = TypeCallbacks([('struct inactive_task_frame', _FetchRegistersInactiveFrame.enable)],
                         wait_for_target=False)
msymbol_cbs = MinimalSymbolCallbacks([('thread_return', _FetchRegistersThreadReturn.enable)],
                                     wait_for_target=False)

register_target(X8664ThreadReturnTarget)
register_target(X8664InactiveFrameTarget)
