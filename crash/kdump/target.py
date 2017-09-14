# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
from kdumpfile import kdumpfile, KDUMP_KVADDR
from kdumpfile.exceptions import *
import addrxlat
from crash.types.list import list_for_each_entry
from crash.types.percpu import get_percpu_var
from crash.types.task import LinuxTask
import crash.cache.tasks
import crash.arch
import crash.arch.x86_64

if sys.version_info.major >= 3:
    long = int

LINUX_KERNEL_PID = 1

class SymbolCallback(object):
    "addrxlat symbolic callback"

    def __init__(self, ctx=None, *args, **kwargs):
        super(SymbolCallback, self).__init__(*args, **kwargs)
        self.ctx = ctx

    def __call__(self, symtype, *args):
        if self.ctx is not None:
            try:
                return self.ctx.next_cb_sym(symtype, *args)
            except addrxlat.BaseException:
                self.ctx.clear_err()

        if symtype == addrxlat.SYM_VALUE:
            ms = gdb.lookup_minimal_symbol(args[0])
            if ms is not None:
                return long(ms.value().address)

        raise addrxlat.NoDataError()

class Target(gdb.Target):
    def __init__(self, filename, debug=False):
        self.filename = filename
        self.arch = None
        self.debug = debug
        try:
            self.kdump = kdumpfile(filename)
        except OSErrorException as e:
            raise RuntimeError(str(e))
        ctx = self.kdump.get_addrxlat_ctx()
        ctx.cb_sym = SymbolCallback(ctx)
        self.kdump.attr['addrxlat.ostype'] = 'linux'

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
        runqueues = gdb.lookup_global_symbol('runqueues')

        rqs = get_percpu_var(runqueues)
        rqscurrs = {long(x["curr"]) : k for (k, x) in rqs.items()}

        self.pid_to_task_struct = {}

        print("Loading tasks...", end='')
        sys.stdout.flush()

        task_count = 0
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
            except gdb.error as e:
                print("Failed to setup task @{:#x}".format(long(task.address)))
                continue
            thread.name = task['comm'].string()

            self.arch.setup_thread_info(thread)
            ltask.attach_thread(thread)
            ltask.set_get_stack_pointer(self.arch.get_stack_pointer)

            crash.cache.tasks.cache_task(ltask)

            task_count += 1
            if task_count % 100 == 0:
                print(".", end='')
                sys.stdout.flush()
        print(" done. ({} tasks total)".format(task_count))

        gdb.selected_inferior().executing = False

    @classmethod
    def report_error(cls, addr, length, error):
        print("Error while reading {:d} bytes from {:#x}: {}"
              .format(length, addr, str(error)),
              file=sys.stderr)

    def to_xfer_partial(self, obj, annex, readbuf, writebuf, offset, ln):
        ret = -1
        if obj == self.TARGET_OBJECT_MEMORY:
            try:
                r = self.kdump.read(KDUMP_KVADDR, offset, ln)
                readbuf[:] = r
                ret = ln
            except EOFException as e:
                if self.debug:
                    self.report_error(offset, ln, e)
                raise gdb.TargetXferEof(str(e))
            except NoDataException as e:
                if self.debug:
                    self.report_error(offset, ln, e)
                raise gdb.TargetXferUnavailable(str(e))
            except AddressTranslationException as e:
                if self.debug:
                    self.report_error(offset, ln, e)
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
        self.arch.fetch_register(thread, register.regnum)
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
