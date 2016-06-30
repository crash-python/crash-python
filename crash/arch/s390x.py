#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.arch import CrashArchitecture, register

class s390xArchitecture(CrashArchitecture):
    ident = "s390:64-bit"
    aliases = [ "s390x" ]
    ulong_type = gdb.lookup_type('unsigned long')

    def __init__(self):
        self.archident = "s390:64-bit"
        self.lowcore_loaded = False
        self.cpu_to_lowcore = {}
        self.task_to_cpu = {}
        thread_info_type = gdb.lookup_type('struct thread_info')
        self.thread_info_p_type = thread_info_type.pointer()

    def setup_thread_info(self, thread):
        task = thread.info.task_struct
        thread_info = task['stack'].cast(self.thread_info_p_type)
        thread.info.set_thread_info(thread_info)

    def ensure_lowcore(self):
        if self.lowcore_loaded: return
        lcs = gdb.lookup_global_symbol("lowcore_ptr").value()
        for i in range(0, lcs.type.range()[1]+2):
            lc = lcs[i]
            if long(lc) == 0L: break
            cpu = long(lc["cpu_nr"])
            self.cpu_to_lowcore[cpu] = lc
            self.task_to_cpu[long(lc["current_task"])] = cpu

        self.lowcore_loaded = True


    def fetch_register_active(self, thread, register):
        self.ensure_lowcore()
        taskp = long(thread.info.task_struct.address)
        if not taskp in self.task_to_cpu:
            gdb.write("task %lx not found in lowcore!" % taskp)

        lc = self.cpu_to_lowcore[self.task_to_cpu[taskp]]
        regs = { "r%d"%x:x for x in range(0,16)}

        if register.name in regs:
            thread.registers[register.name].value = lc["gpregs_save_area"][regs[register.name]]
        elif register.name == 'pswa':
            thread.registers["pswa"].value = lc["psw_save_area"]["addr"]

    def fetch_register_scheduled(self, thread, register):
        ulong_type = self.ulong_type
        task = thread.info.task_struct

        ksp = task['thread']['ksp'].cast(ulong_type.pointer())
        rip = (ksp+17).dereference().cast(ulong_type.pointer())
        if register.name == 'pswa':
            thread.registers["pswa"].value = rip
            return True
        ksp = (ksp+18).dereference().cast(ulong_type.pointer())
        regmap = {"r%d"%i: i+3 for i in range(1,16)}
        if register.name in regmap:
            thread.registers[register.name].value = (ksp + regmap[register.name]).dereference()

    def get_stack_pointer(self, thread):
        task = thread.info.task_struct
        ksp = task['thread']['ksp'].cast(ulong_type.pointer())
        ksp = (ksp+18).dereference().cast(ulong_type.pointer())
        return long(ksp)

register(s390xArchitecture)
