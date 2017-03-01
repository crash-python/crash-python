#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from kdumpfile import kdumpfile
from kdumpfile import KDUMP_KVADDR
from kdumpfile.exceptions import *
from crash.types.list import list_for_each_entry
from crash.types.percpu import get_percpu_var
from crash.types.task import LinuxTask
import crash.cache.tasks
import crash.arch

LINUX_KERNEL_PID = 1

def symbol_func(symname):
    ms = gdb.lookup_minimal_symbol(symname)
    if not ms:
        print ("Cannot lookup symbol %s" % symname)
        raise RuntimeError("Cannot lookup symbol %s" % symname)
    return long(ms.value())

class Target(gdb.Target):
    def __init__(self, fil):
        if isinstance(fil, str):
            fil = file(fil)
        self.fil = fil
        print "kdump (%s)" % fil
        self.kdump = kdumpfile(fil)
        self.setup_arch()
        self.kdump.symbol_func = symbol_func
        self.kdump.vtop_init()
        super(Target, self).__init__()
        gdb.execute('set print thread-events 0')
        self.setup_tasks()

    def setup_arch(self):
        archname = self.kdump.attr.arch.name
        archclass = crash.arch.get_architecture(archname)
        if not archclass:
            raise NotImplementedError("Architecture %s is not supported yet." % archname)

        # Doesn't matter what symbol as long as it's everywhere
        # Use vsnprintf since 'printk' can be dropped with CONFIG_PRINTK=n
        sym = gdb.lookup_symbol('vsnprintf', None)[0]
        if sym.symtab.objfile.architecture.name() != archclass.ident:
            raise TypeError("Dump file is for `%s' but provided kernel is for `%s'" \
                            % (archname, archclass.ident))

        self.arch = archclass()

    def setup_tasks(self):
        init_task = gdb.lookup_global_symbol('init_task')
        task_list = init_task.value()['tasks']
        runqueues = gdb.lookup_global_symbol('runqueues')

        rqs = get_percpu_var(runqueues)
        rqscurrs = { long(x["curr"]) : k for (k, x) in rqs.items() }

        self.pid_to_task_struct = {}

        tasks = []
        for taskg in list_for_each_entry(task_list, init_task.type, 'tasks'):
            tasks.append(taskg)
            for task in list_for_each_entry(taskg['thread_group'], init_task.type, 'thread_group'):
                tasks.append(task)

        for task in tasks:
            cpu = None
            regs = None
            active = long(task.address) in rqscurrs
            if active:
                cpu = rqscurrs[long(task.address)]
                regs = self.kdump.attr.cpu[cpu].reg

            ltask = LinuxTask(task, active, cpu, regs)
            ptid = (LINUX_KERNEL_PID, task['pid'], 0)
            try:
                thread = gdb.selected_inferior().new_thread(ptid, ltask)
            except gdb.error:
                print "Failed to setup task %x" % task.address
                continue
            thread.name = task['comm'].string()

            self.arch.setup_thread_info(thread)
            ltask.attach_thread(thread)
            ltask.set_get_stack_pointer(self.arch.get_stack_pointer)

            crash.cache.tasks.cache_task(ltask)

        gdb.selected_inferior().executing = False

    def to_xfer_partial(self, obj, annex, readbuf, writebuf, offset, ln):
        ret = -1
        if obj == self.TARGET_OBJECT_MEMORY:
            try:
                r = self.kdump.read (KDUMP_KVADDR, offset, ln)
                readbuf[:] = r
                ret = ln
            except EOFException, e:
                raise gdb.TargetXferEof(str(e))
            except NoDataException, e:
                raise gdb.TargetXferUnavailable(str(e))
            except AddressTranslationException, e:
                raise gdb.TargetXferUnavailable(str(e))
        else:
            raise IOError("Unknown obj type")
        return ret

    def to_thread_alive(self, ptid):
        return True

    def to_pid_to_str(self, ptid):
        return "pid %d" % ptid[1]

    def to_fetch_registers(self, register):
        thread = gdb.selected_thread()
        self.arch.fetch_register(thread, register.regnum)
        return True

    def to_prepare_to_store(self, thread):
        pass

    # We don't need to store anything; The regcache is already written.
    def to_store_registers(self, thread):
        pass

    def to_has_execution(self, ptid):
        return False
