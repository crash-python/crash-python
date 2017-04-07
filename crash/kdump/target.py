# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from kdumpfile import kdumpfile, KDUMP_KVADDR
from crash.types.util import list_for_each_entry
from kdumpfile.exceptions import *

#arch = "i386:x86-64"
#
#setup = {
#    'i386:x86-64' : setup_thread_amd64,
#}

ulong_type = gdb.lookup_type('unsigned long')
rip = gdb.lookup_minimal_symbol("thread_return").value()

def setup_thread_amd64(thread, task):
    rsp = task['thread']['sp'].cast(ulong_type.pointer())
    rbp = rsp.dereference().cast(ulong_type.pointer())
    rbx = (rbp - 1).dereference()
    r12 = (rbp - 2).dereference()
    r13 = (rbp - 3).dereference()
    r14 = (rbp - 4).dereference()
    r15 = (rbp - 5).dereference()

    # The two pushes that don't have CFI info
#    rsp += 2

#    ex = in_exception_stack(rsp)
#    if ex:
#    print "EXCEPTION STACK: pid %d" % task['pid']

    thread.registers['rsp'].value = rsp
    thread.registers['rbp'].value = rbp
    thread.registers['rip'].value = rip
    thread.registers['rbx'].value = rbx
    thread.registers['r12'].value = r12
    thread.registers['r13'].value = r13
    thread.registers['r14'].value = r14
    thread.registers['r15'].value = r15
    thread.registers['cs'].value = 2*8
    thread.registers['ss'].value = 3*8

def symbol_func(symname):
    ms = gdb.lookup_minimal_symbol(symname)
    if not ms:
        print(("Cannot lookup symbol %s" % symname))
        raise RuntimeError("Cannot lookup symbol %s" % symname)
    return int(ms.value())

class Target(gdb.Target):
    def __init__(self, fil):
        if isinstance(fil, str):
            fil = file(fil)
            self.fil = fil
            print("kdump (%s)" % fil)
            self.kdump = kdumpfile(fil)
            self.kdump.symbol_func = symbol_func
            self.kdump.vtop_init()
            super(Target, self).__init__()
	    gdb.execute('set print thread-events 0')
	    self.setup_tasks()

    def setup_tasks(self):
        init_task = gdb.lookup_global_symbol('init_task')
        task_list = init_task.value()['tasks']

        self.pid_to_task_struct = {}

        for task in list_for_each_entry(task_list, init_task.type, 'tasks'):
            thread = gdb.selected_inferior().new_thread((1, task['pid'], 0), task)
            thread.name = task['comm'].string()

        gdb.selected_inferior().executing = False

    def to_xfer_partial(self, obj, annex, readbuf, writebuf, offset, ln):
        ret = -1
        if obj == self.TARGET_OBJECT_MEMORY:
	    try:
		r = self.kdump.read (KDUMP_KVADDR, offset, ln)
		readbuf[:] = r
		ret = ln
	    except EOFException as e:
		raise gdb.TargetXferEof(str(e))
	    except NoDataException as e:
		raise gdb.TargetXferUnavailable(str(e))
	else:
	    raise IOError("Unknown obj type")
        return ret

    def to_thread_alive(self, ptid):
        return 1

    def to_pid_to_str(self, ptid):
        return "pid %d" % ptid[1]

    def to_fetch_registers(self, register):
        thread = gdb.selected_thread()
        setup_thread_amd64(thread, thread.info)
        return True

    def to_prepare_to_store(self, thread):
        pass

    # We don't need to store anything; The regcache is already written.
    def to_store_registers(self, thread):
        pass

    def to_has_execution(self, ptid):
        return False
