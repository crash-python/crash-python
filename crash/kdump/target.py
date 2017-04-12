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

class Target(gdb.Target):
    def __init__(self, filename):
        self.filename = filename
        self.arch = None
        try:
            self.kdump = kdumpfile(filename)
        except SysErrException as e:
            raise RuntimeError(str(e))
        self.kdump.vtop_init()

        gdb.execute('set print thread-events 0')

        self.setup_arch()

        # So far we've read from the kernel image, now that we've setup
        # the architecture, we're ready to plumb into the target
        # infrastructure.
        super(Target, self).__init__()

        # Now we're reading from the dump file
        self.setup_tasks()

    def setup_arch(self):
        archname = self.kdump.attr.arch.name
        archclass = crash.arch.get_architecture(archname)
        if not archclass:
            raise NotImplementedError("Architecture {} is not supported yet."
                                      .format(archname))

        # Doesn't matter what symbol as long as it's everywhere
        # Use vsnprintf since 'printk' can be dropped with CONFIG_PRINTK=n
        sym = gdb.lookup_symbol('vsnprintf', None)[0]
        if sym is None:
            raise RuntimeError("Missing vsnprintf indicates there is no kernel image loaded.")
        if sym.symtab.objfile.architecture.name() != archclass.ident:
            raise TypeError("Dump file is for `{}' but provided kernel is for `{}'"
                            .format(archname, archclass.ident))

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
                r = self.kdump.read(KDUMP_KVADDR, offset, ln)
                readbuf[:] = r
                ret = ln
            except EOFException as e:
                raise gdb.TargetXferEof(str(e))
            except NoDataException as e:
                raise gdb.TargetXferUnavailable(str(e))
            except AddressTranslationException as e:
                raise gdb.TargetXferUnavailable(str(e))
        else:
            raise IOError("Unknown obj type")
        return ret

    @staticmethod
    def to_thread_alive(ptid):
        return True

    @staticmethod
    def to_pid_to_str(ptid):
        return "pid {:d}".format(ptid[1])

    def to_fetch_registers(self, register):
        thread = gdb.selected_thread()
        self.arch.setup_thread(thread)
        return True

    @staticmethod
    def to_prepare_to_store(thread):
        pass

    # We don't need to store anything; The regcache is already written.
    @staticmethod
    def to_store_registers(thread):
        pass

    @staticmethod
    def to_has_execution(ptid):
        return False
