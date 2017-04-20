# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import gdb
import sys

if sys.version_info.major >= 3:
    long = int

from crash.infra import delayed_init

PF_EXITING = long(0x4)

def get_value(symname):
    sym = gdb.lookup_symbol(symname, block=None, domain=gdb.SYMBOL_VAR_DOMAIN)
    if sym[0]:
        return sym[0].value()

@delayed_init
class TaskStateFlags(object):
    valid = False

    def __init__(self):
        self.discover_flags()

    @classmethod
    def _discover_flags(cls):
        task_struct = gdb.lookup_type('struct task_struct')
        task_state = get_value('task_state_array')
        charp = gdb.lookup_type('char').pointer()

        if task_state:
            count = task_state.type.sizeof // charp.sizeof

            bit = 0
            for i in range(count):
                state = task_state[i].string()
                state_strings = {
                    '(running)'      : 'TASK_RUNNING',
                    '(sleeping)'     : 'TASK_INTERRUPTIBLE',
                    '(disk sleep)'   : 'TASK_UNINTERRUPTIBLE',
                    '(stopped)'      : 'TASK_STOPPED',
                    '(zombie)'       : 'TASK_ZOMBIE',
                    #'(dead)'        : 'TASK_DEAD',
                    '(swapping)'     : 'TASK_SWAPPING',
                    #'(tracing stop)' : 'TASK_TRACING_STOPPED',
                    '(wakekill)'     : 'TASK_WAKEKILL',
                    '(waking)'       : 'TASK_WAKING',
                }

                for key in state_strings:
                    if key in state:
                        setattr(cls, state_strings[key], bit)
                    if '(dead)' in state:
                        cls.TASK_DEAD = bit
                    if '(tracing stop)' in state:
                        cls.TASK_TRACING_STOPPED = bit
                if bit == 0:
                    bit = 1
                else:
                    bit <<= 1
        else:
            # Sane defaults
            cls.TASK_RUNNING = 0
            cls.TASK_INTERRUPTIBLE = 1
            cls.TASK_UNINTERRUPTIBLE = 2
            cls.TASK_ZOMBIE = 4
            cls.TASK_STOPPED = 8
            cls.TASK_SWAPPING = 16
            cls.TASK_EXCLUSIVE = 32

        cls.check_state_bits()
        cls.valid = True

    @classmethod
    def discover_flags(cls):
        if not cls.valid:
            cls._discover_flags()

    @classmethod
    def check_state_bits(cls):
        required = [
            'TASK_RUNNING',
            'TASK_INTERRUPTIBLE',
            'TASK_UNINTERRUPTIBLE',
            'TASK_ZOMBIE',
            'TASK_STOPPED',
        ]

        missing = []

        for bit in required:
            if not hasattr(cls, bit):
                missing.append(bit)

        if len(missing):
            raise RuntimeError("Missing required task states: {}"
                               .format(",".join(missing)))

TF = TaskStateFlags

class BadTaskError(TypeError):
    msgtemplate = "task_struct must be gdb.Value describing struct task_struct not {}"
    def __init__(self, task):
        if isinstance(task, gdb.Value):
            typedesc = task.type
        else:
            typedesc = type(task)
        self(BadTaskError, task).__init__(msgtemplate.format(typedesc))

@delayed_init
class LinuxTask(object):
    task_struct_type = None
    mm_struct_fields = None
    get_rss = None
    get_stack_pointer_fn = None
    valid = False

    def __init__(self, task_struct, active=False, cpu=None, regs=None):
        flags = TaskStateFlags.discover_flags()

        self.init_task_types(task_struct)

        if cpu is not None and not isinstance(cpu, int):
            raise TypeError("cpu must be integer or None")

        if not (isinstance(task_struct, gdb.Value) and
                (task_struct.type == self.task_struct_type or
                 task_struct.type == self.task_struct_type.pointer())):
                raise BadTaskError(task_struct)

        self.task_struct = task_struct
        self.active = active
        self.cpu = cpu
        self.regs = regs

        self.thread_info = None
        self.stack_pointer = None
        self.thread = None

        # mem data
        self.mem_valid = False
        self.rss = 0
        self.total_vm = 0
        self.pgd_addr = 0

    @classmethod
    def init_task_types(cls, task):
        if not cls.valid:
            t = gdb.lookup_type('struct task_struct')
            if task.type != t:
                raise BadTaskError(task_struct)

            # Using a type within the same context makes things a *lot* faster
            # This works around a shortcoming in gdb.  A type lookup and
            # a type resolved from a symbol will be different structures
            # within gdb.  Equality requires a deep comparison rather than
            # a simple pointer comparison.
            cls.task_struct_type = task.type
            fields = cls.task_struct_type.fields()
            cls.task_state_has_exit_state = 'exit_state' in fields
            cls.mm_struct_fields = gdb.lookup_type('struct mm_struct').keys()
            cls.pick_get_rss()
            cls.pick_last_run()
            cls.init_mm = get_value('init_mm')
            cls.valid = True

    def attach_thread(self, thread):
        if not isinstance(thread, gdb.InferiorThread):
            raise TypeError("Expected gdb.InferiorThread")
        self.thread = thread

    def set_thread_info(self, thread_info):
        self.thread_info = thread_info

    def get_thread_info(self):
        return self.thread_info

    def task_state(self):
        state = long(self.task_struct['state'])
        if self.task_state_has_exit_state:
            state |= long(self.task_struct['exit_state'])
        return state

    def maybe_dead(self):
        state = self.task_state()

        known = TF.TASK_INTERRUPTIBLE
        known |= TF.TASK_UNINTERRUPTIBLE
        known |= TF.TASK_ZOMBIE
        known |= TF.TASK_STOPPED

        if hasattr(TF, 'TASK_SWAPPING'):
            known |= TF.TASK_SWAPPING
        return (state & known) == 0

    def task_flags(self):
        return long(self.task_struct['flags'])

    def is_exiting(self):
        return self.task_flags() & PF_EXITING

    def is_zombie(self):
        return self.task_state() & TF.TASK_ZOMBIE

    def update_mem_usage(self):
        if self.mem_valid:
            return

        if self.is_zombie() or self.is_exiting():
            return

        mm = self.task_struct['mm']
        if not mm:
            self.mem_valid = True
            return

        self.rss = self.get_rss()
        self.total_vm = long(mm['total_vm'])
        self.pgd_addr = long(mm['pgd'])
        self.mem_valid = True

    def is_kernel_task(self):
        if self.task_struct['pid'] == 0:
            return True

        if self.is_zombie() or self.is_exiting():
            return False

        mm = self.task_struct['mm']
        if mm == 0:
            return True
        elif self.init_mm and mm == self.init_mm.address:
            return True

        return False

    @classmethod
    def set_get_stack_pointer(cls, fn):
        cls.get_stack_pointer_fn = fn

    @classmethod
    def get_stack_pointer(cls):
        # This unbinds the function from the task object so we don't
        # pass self to the function.
        fn = cls.get_stack_pointer_fn
        return fn(self.thread)

    def get_rss_field(self):
        return long(self.task_struct['mm']['rss'].value())

    def get__rss_field(self):
        return long(self.task_struct['mm']['_rss'].value())

    def get_rss_stat_field(self):
        stat = self.task_struct['mm']['rss_stat']['count']
        stat0 = self.task_struct['mm']['rss_stat']['count'][0]
        rss = 0
        for i in range(stat.type.sizeof // stat[0].type.sizeof):
            rss += long(stat[i]['counter'])
        return rss

    def get_anon_file_rss_fields(self):
        mm = self.task_struct['mm']
        rss = 0
        for name in ['_anon_rss', '_file_rss']:
            if name in mm_struct_fields:
                if mm[name].type == self.atomic_long_type:
                    rss += long(mm[name]['counter'])
                else:
                    rss += long(mm[name])
        return rss

    # The Pythonic way to do this is by generating the LinuxTask class
    # dynamically.  We may do that eventually, but for now we can just
    # select the proper function and assign it to the class.
    @classmethod
    def pick_get_rss(cls):
        if 'rss' in cls.mm_struct_fields:
            cls.get_rss = cls.get_rss_field
        elif '_rss' in cls.mm_struct_fields:
            cls.get_rss = cls.get__rss_field
        elif 'rss_stat' in cls.mm_struct_fields:
            cls.MM_FILEPAGES = get_value('MM_FILEPAGES')
            cls.MM_ANONPAGES = get_value('MM_ANONPAGES')
            cls.get_rss = cls.get_rss_stat_field
        elif '_anon_rss' in cls.mm_struct_fields or \
             '_file_rss' in cls.mm_struct_fields:
            cls.atomic_long_type = gdb.lookup_type('atomic_long_t')
            cls.get_rss = cls.get_anon_file_rss_fields
        else:
            raise RuntimeError("No method to retrieve RSS from task found.")

    def last_run__last_run(self):
        return long(self.task_struct['last_run'])

    def last_run__timestamp(self):
        return long(self.task_struct['timestamp'])

    def last_run__last_arrival(self):
        return long(self.task_struct['sched_info']['last_arrival'])

    @classmethod
    def pick_last_run(cls):
        fields = cls.task_struct_type.keys()
        if ('sched_info' in fields and
                'last_arrival' in cls.task_struct_type['sched_info'].type.keys()):
            cls.last_run = cls.last_run__last_arrival

        elif 'last_run' in fields:
            cls.last_run = cls.last_run__last_run

        elif 'timestamp' in fields:
            cls.last_run = cls.last_run__timestamp
        else:
            raise RuntimeError("No method to retrieve last run from task found.")
