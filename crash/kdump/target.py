# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from kdumpfile import kdumpfile, KDUMP_KVADDR
from kdumpfile.exceptions import *
from crash.types.list import list_for_each_entry

import crash.arch
import crash.arch.x86_64

def symbol_func(symname):
    ms = gdb.lookup_minimal_symbol(symname)
    if not ms:
        print("Cannot lookup symbol {}".format(symname))
        raise RuntimeError("Cannot lookup symbol {}".format(symname))
    return int(ms.value())

class Target(gdb.Target):
    def __init__(self, fil):
        if isinstance(fil, str):
            fil = file(fil)
            self.fil = fil
            print("kdump ({})".format(fil))
            self.kdump = kdumpfile(fil)
            self.setup_arch()
            self.kdump.symbol_func = symbol_func
            self.kdump.vtop_init()
            super(Target, self).__init__()
            gdb.execute('set print thread-events 0')
            self.setup_tasks()

    def setup_arch(self):
        archname = self.kdump.attr("arch")['name']
        archclass = crash.arch.get_architecture(archname)
        if not archclass:
            raise NotImplementedError("Architecture %s is not supported yet." % archname)

        self.arch = archclass()

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
        return True

    def to_pid_to_str(self, ptid):
        return "pid {:d}".format(ptid[1])

    def to_fetch_registers(self, register):
        thread = gdb.selected_thread()
        self.arch.setup_thread(thread)
        return True

    def to_prepare_to_store(self, thread):
        pass

    # We don't need to store anything; The regcache is already written.
    def to_store_registers(self, thread):
        pass

    def to_has_execution(self, ptid):
        return False
