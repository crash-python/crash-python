# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Optional
import re
import sys

import gdb

from crash.arch import CrashArchitecture, KernelFrameFilter, register_arch
from crash.arch import FetchRegistersCallback
from crash.util.symbols import Types, MinimalSymvals
from crash.util.symbols import TypeCallbacks, MinimalSymbolCallbacks

types = Types(['struct inactive_task_frame *', 'struct thread_info *',
               'unsigned long *'])
msymvals = MinimalSymvals(['thread_return'])

# pylint: disable=abstract-method
class _FetchRegistersBase(FetchRegistersCallback):
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

# pylint: disable=abstract-method
class _FRC_inactive_task_frame(_FetchRegistersBase):
    def fetch_scheduled(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        registers: gdb.RegisterCollectionType = {}
        task = thread.info.task_struct

        rsp = task['thread']['sp'].cast(types.unsigned_long_p_type)

        rsp = thread.arch.adjust_scheduled_frame_offset(rsp)

        registers['rsp'] = rsp

        frame = rsp.cast(types.inactive_task_frame_p_type).dereference()

        registers['rip'] = thread.arch.get_scheduled_rip()
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

class _FRC_thread_return(_FetchRegistersBase):
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

class x86_64Architecture(CrashArchitecture):
    ident = "i386:x86-64"
    aliases = ["x86_64"]

    _frame_offset: Optional[int] = None

    def __init__(self) -> None:
        super(x86_64Architecture, self).__init__()

        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

        self._scheduled_rip: int

    def setup_thread_info(self, thread: gdb.InferiorThread) -> None:
        task = thread.info.task_struct
        thread_info = task['stack'].cast(types.thread_info_p_type)
        thread.info.set_thread_info(thread_info)

    # We don't have CFI for __switch_to_asm but we do know what it looks like.
    # We push 6 registers and then swap rsp, so we can just rewind back
    # to __switch_to_asm getting called and then populate the registers that
    # were saved on the stack.
    def setup_scheduled_frame_offset(self, task: gdb.Value) -> None:
        if self._frame_offset:
            return

        top = int(task['stack']) + 16*1024
        callq = re.compile("callq?.*<(\w+)>")

        orig_rsp = rsp = task['thread']['sp'].cast(types.unsigned_long_p_type)

        count = 0
        while int(rsp) < top:
            val = int(rsp.dereference()) - 5
            if val > self.filter.address:
                try:
                    insn = gdb.execute(f"x/i {val:#x}", to_string=True)
                except Exception as e:
                    rsp += 1
                    count += 1
                    continue

                if not insn:
                    continue

                m = callq.search(insn)
                if m and m.group(1) == "__switch_to_asm":
                    self._frame_offset = rsp - orig_rsp  + 1
                    self._scheduled_rip = val
                    return

            rsp += 1
            count += 1

        raise RuntimeError("Cannot locate stack frame offset for __schedule")

    def adjust_scheduled_frame_offset(self, rsp: gdb.Value) -> gdb.Value:
        if self._frame_offset:
            return rsp + self._frame_offset
        return rsp

    def get_scheduled_rip(self) -> int:
        return self._scheduled_rip

    @classmethod
    # pylint: disable=unused-argument
    def setup_inactive_task_frame_handler(cls, inactive: gdb.Type) -> None:
        cls.set_fetch_registers(_FRC_inactive_task_frame)

    @classmethod
    # pylint: disable=unused-argument
    def setup_thread_return_handler(cls, inactive: gdb.Type) -> None:
        cls.set_fetch_registers(_FRC_thread_return)

    @classmethod
    def get_stack_pointer(cls, thread_struct: gdb.Value) -> int:
        return int(thread_struct['sp'])

type_cbs = TypeCallbacks([('struct inactive_task_frame',
                           x86_64Architecture.setup_inactive_task_frame_handler)])
msymbol_cbs = MinimalSymbolCallbacks([('thread_return',
                                       x86_64Architecture.setup_thread_return_handler)])

register_arch(x86_64Architecture)
