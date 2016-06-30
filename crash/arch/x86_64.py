#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.arch import CrashArchitecture, register

class x86_64Architecture(CrashArchitecture):
    ident = "i386:x86-64"
    aliases = [ "x86_64" ]
    # register position on stack (in the future, this should be generated
    # dynamically)
    stackregs = {"rbx": 1,
                 "r12": 2,
                 "r13": 3,
                 "r14": 4,
                 "r15": 5}

    def __init__(self):
        # PC for blocked threads
        self.rip = gdb.lookup_minimal_symbol("thread_return").value()
        self.ulong_type = gdb.lookup_type('unsigned long')
        thread_info_type = gdb.lookup_type('struct thread_info')
        self.thread_info_p_type = thread_info_type.pointer()

    def setup_thread_info(self, thread):
        task = thread.info.task_struct
        thread_info = task['stack'].cast(self.thread_info_p_type)
        thread.info.set_thread_info(thread_info)

    def fetch_register_active(self, thread, register):
        task = thread.info
        for reg in task.regs:
            if reg == "rip" and (register.name != "rip"):
                continue
            if reg in ["gs_base", "orig_ax", "rflags", "fs_base"]:
                continue
            thread.registers[reg].value = task.regs[reg]

    def fetch_register_scheduled(self, thread, register):
        ulong_type = self.ulong_type
        task = thread.info.task_struct
        r = register.name

        # Only write rip when requested; It resets the frame cache
        if r == 'rip':
            thread.registers['rip'].value = self.rip
            return True

        rsp = task['thread']['sp'].cast(ulong_type.pointer())
        rbp = rsp.dereference().cast(ulong_type.pointer())

        if r in self.stackregs:
            thread.registers[r].value = (rbp - self.stackregs[r]).dereference()
        elif r == 'rsp':
            thread.registers[r].value = rsp
            thread.info.stack_pointer = rsp
            thread.info.valid_stack = True
        elif r == 'rbp':
            thread.registers[r].value = rbp

       # The two pushes that don't have CFI info
        # rsp += 2

        # ex = in_exception_stack(rsp)
        # if ex:
        #     print "EXCEPTION STACK: pid %d" % task['pid']

        elif r == 'cs':
            thread.registers['cs'].value = 2*8
        elif r == 'ss':
            thread.registers['ss'].value = 3*8
        else:
            gdb.write("wanted register %s\n" % r)
            return False

        return True

    def get_stack_pointer(self, thread):
        return long(thread.registers['rsp'].value)

register(x86_64Architecture)
