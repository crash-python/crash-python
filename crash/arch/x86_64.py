# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.arch import CrashArchitecture, KernelFrameFilter, register_arch
from crash.arch import FetchRegistersCallback
from crash.util.symbols import Types, MinimalSymvals
from crash.util.symbols import TypeCallbacks, MinimalSymbolCallbacks

import gdb

types = Types(['struct inactive_task_frame *', 'struct thread_info *',
               'unsigned long *'])
msymvals = MinimalSymvals(['thread_return'])

# pylint: disable=abstract-method
class _FetchRegistersBase(FetchRegistersCallback):
    def fetch_active(self, thread: gdb.InferiorThread, register: int) -> None:
        task = thread.info
        for reg in task.regs:
            if reg == "rip" and register not in (16, -1):
                continue
            try:
                thread.registers[reg].value = task.regs[reg]
            except KeyError:
                pass

# pylint: disable=abstract-method
class _FRC_inactive_task_frame(_FetchRegistersBase):
    def fetch_scheduled(self, thread: gdb.InferiorThread,
                        register: int) -> None:
        task = thread.info.task_struct

        rsp = task['thread']['sp'].cast(types.unsigned_long_p_type)
        thread.registers['rsp'].value = rsp

        frame = rsp.cast(types.inactive_task_frame_p_type).dereference()

        # Only write rip when requested; It resets the frame cache
        if register in (16, -1):
            thread.registers['rip'].value = frame['ret_addr']
            if register == 16:
                return

        thread.registers['rbp'].value = frame['bp']
        thread.registers['rbx'].value = frame['bx']
        thread.registers['r12'].value = frame['r12']
        thread.registers['r13'].value = frame['r13']
        thread.registers['r14'].value = frame['r14']
        thread.registers['r15'].value = frame['r15']
        thread.registers['cs'].value = 2*8
        thread.registers['ss'].value = 3*8

        thread.info.stack_pointer = rsp
        thread.info.valid_stack = True

class _FRC_thread_return(_FetchRegistersBase):
    def __call__(self, thread: gdb.InferiorThread,
                 register: gdb.Register) -> None:
        task = thread.info.task_struct

        # Only write rip when requested; It resets the frame cache
        if register in (16, -1):
            thread.registers['rip'].value = msymvals.thread_return
            if register == 16:
                return

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

        thread.registers['rsp'].value = rsp
        thread.registers['rbp'].value = rbp
        thread.registers['rbx'].value = rbx
        thread.registers['r12'].value = r12
        thread.registers['r13'].value = r13
        thread.registers['r14'].value = r14
        thread.registers['r15'].value = r15
        thread.registers['cs'].value = 2*8
        thread.registers['ss'].value = 3*8

        thread.info.stack_pointer = rsp
        thread.info.valid_stack = True

class x86_64Architecture(CrashArchitecture):
    ident = "i386:x86-64"
    aliases = ["x86_64"]

    def __init__(self) -> None:
        super(x86_64Architecture, self).__init__()

        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

    def setup_thread_info(self, thread: gdb.InferiorThread) -> None:
        task = thread.info.task_struct
        thread_info = task['stack'].cast(types.thread_info_p_type)
        thread.info.set_thread_info(thread_info)

    @classmethod
    # pylint: disable=unused-argument
    def setup_inactive_task_frame_handler(cls, inactive: gdb.Type) -> None:
        cls.set_fetch_registers(_FRC_inactive_task_frame)

    @classmethod
    # pylint: disable=unused-argument
    def setup_thread_return_handler(cls, inactive: gdb.Type) -> None:
        cls.set_fetch_registers(_FRC_thread_return)

    @classmethod
    def get_stack_pointer(cls, thread_struct: gdb.Value) -> gdb.Value:
        return thread_struct['sp']

type_cbs = TypeCallbacks([('struct inactive_task_frame',
                           x86_64Architecture.setup_inactive_task_frame_handler)])
msymbol_cbs = MinimalSymbolCallbacks([('thread_return',
                                       x86_64Architecture.setup_thread_return_handler)])

register_arch(x86_64Architecture)
