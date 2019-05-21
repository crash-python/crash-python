# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.arch import CrashArchitecture, register, KernelFrameFilter

class x86_64Architecture(CrashArchitecture):
    ident = "i386:x86-64"
    aliases = ["x86_64"]

    def __init__(self):
        super(x86_64Architecture, self).__init__()
        # PC for blocked threads
        try:
            inactive = gdb.lookup_type('struct inactive_task_frame')
            self.fetch_register_scheduled = \
                self.fetch_register_scheduled_inactive
            self.inactive_task_frame_type = inactive
        except gdb.error as e:
            try:
                thread_return = gdb.lookup_minimal_symbol("thread_return")
                self.thread_return = thread_return.value().address
                self.fetch_register_scheduled = \
                    self.fetch_register_scheduled_thread_return
            except Exception:
                raise RuntimeError("{} requires symbol 'thread_return'"
                                   .format(self.__class__.__name__))
        self.ulong_type = gdb.lookup_type('unsigned long')
        thread_info_type = gdb.lookup_type('struct thread_info')
        self.thread_info_p_type = thread_info_type.pointer()

        # Stop stack traces with addresses below this
        self.filter = KernelFrameFilter(0xffff000000000000)

    def setup_thread_info(self, thread: gdb.InferiorThread) -> None:
        task = thread.info.task_struct
        thread_info = task['stack'].cast(self.thread_info_p_type)
        thread.info.set_thread_info(thread_info)

    def fetch_register_active(self, thread: gdb.InferiorThread,
                              register: gdb.Register) -> None:
        task = thread.info
        for reg in task.regs:
            if reg == "rip" and (register != 16 and register != -1):
                continue
            try:
                thread.registers[reg].value = task.regs[reg]
            except KeyError as e:
                pass

    def fetch_register_scheduled_inactive(self, thread: gdb.InferiorThread,
                                          register: gdb.Register) -> None:
        ulong_type = self.ulong_type
        task = thread.info.task_struct

        rsp = task['thread']['sp'].cast(ulong_type.pointer())
        thread.registers['rsp'].value = rsp

        frame = rsp.cast(self.inactive_task_frame_type.pointer()).dereference()

        # Only write rip when requested; It resets the frame cache
        if register == 16 or register == -1:
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

    def fetch_register_scheduled_thread_return(self, thread: gdb.InferiorThread,
                                               register: gdb.Register):
        ulong_type = self.ulong_type
        task = thread.info.task_struct

        # Only write rip when requested; It resets the frame cache
        if register == 16 or register == -1:
            thread.registers['rip'].value = self.thread_return
            if register == 16:
                return True

        rsp = task['thread']['sp'].cast(ulong_type.pointer())
        rbp = rsp.dereference().cast(ulong_type.pointer())
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

    @classmethod
    def get_stack_pointer(cls, thread_struct: gdb.Value) -> gdb.Value:
        return thread_struct['sp']

register(x86_64Architecture)
