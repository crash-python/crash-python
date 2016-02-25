#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

def get_value(symname):
    sym = gdb.lookup_symbol(symname, block=None, domain=gdb.SYMBOL_VAR_DOMAIN)
    return sym[0].value()


PF_EXITING = 0x4L
class LinuxTask:
    task_struct_type = None
    mm_struct_fields = None
    task_state_has_exit_state = None

    TASK_RUNNING = None
    TASK_INTERRUPTIBLE = None
    TASK_UNINTERRIBLE = None
    TASK_ZOMBIE = None
    TASK_STOPPED = None
    TASK_SWAPPING = None
    TASK_EXCLUSIVE = None
    TASK_DEAD = None

    TASK_SWAPPING = None
    TASK_TRACING_STOPPED = None
    TASK_WAKEKILL = None
    TASK_WAKING = None

    get_rss = None
    get_stack_pointer = None
    initialized = False

    def __init__(self, task_struct, active = False,
                 cpu = None, regs = None):

        # We only want to do this once on instantiation
        if self.__class__.initialized == False:
            self.init_task_types()

        if cpu is not None and not isinstance(cpu, int):
            raise TypeError("cpu must be integer or None")

        if not isinstance(task_struct, gdb.Value) or \
           not task_struct.type != self.task_struct_type:
            raise TypeError("task_struct must be gdb.Value describing struct task_struct")

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

    def set_default_task_states(self):
        self.__class__.TASK_RUNNING         = 0
        self.__class__.TASK_INTERRUPTIBLE   = 1
        self.__class__.TASK_UNINTERRUPTIBLE = 2
        self.__class__.TASK_ZOMBIE          = 4
        self.__class__.TASK_STOPPED         = 8
        self.__class__.TASK_SWAPPING        = 16
        self.__class__.TASK_EXCLUSIVE       = 32

    def init_task_types(self):
        self.__class__.task_struct_type = gdb.lookup_type('struct task_struct')
        charp = gdb.lookup_type('char').pointer()
        task_state = get_value('task_state_array')

        fields = self.task_struct_type.fields()
        self.__class__.task_state_has_exit_state = 'exit_state' in fields

        if not task_state:
            self.set_default_task_states()
        else:
            count = task_state.type.sizeof / charp.sizeof
            self.__class__.TASK_DEAD = 0
            self.__class__.TASK_TRACING_STOPPED = 0

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
                        setattr(self.__class__, state_strings[key], bit)
                    if '(dead)' in state:
                        self.__class__.TASK_DEAD |= bit
                    if '(tracing stop)' in state:
                        self.__class__.TASK_TRACING_STOPPED |= bit
                if bit == 0:
                    bit = 1
                else:
                    bit <<= 1

        if self.TASK_RUNNING is None or \
           self.TASK_INTERRUPTIBLE is None or \
           self.TASK_UNINTERRUPTIBLE is None or \
           self.TASK_ZOMBIE is None or \
           self.TASK_STOPPED is None:
            print self.TASK_RUNNING
            print self.TASK_INTERRUPTIBLE
            print self.TASK_UNINTERRUPTIBLE
            print self.TASK_ZOMBIE
            print self.TASK_STOPPED
            raise RuntimeError("Missing required task states.")

        self.__class__.mm_struct_fields = gdb.lookup_type('struct mm_struct').keys()
        self.__class__.get_rss = self.which_get_rss()
        self.__class__.last_run = self.which_last_run()
        self.__class__.init_mm = get_value('init_mm')
        self.__class__.initialized = True

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

        known  = self.TASK_INTERRUPTIBLE
        known |= self.TASK_UNINTERRUPTIBLE
        known |= self.TASK_ZOMBIE
        known |= self.TASK_STOPPED

        if self.TASK_SWAPPING:
            known |= self.TASK_SWAPPING
        return (state & known) == 0

    def task_flags(self):
        return long(self.task_struct['flags'])

    def is_exiting(self):
        return self.task_flags() & PF_EXITING

    def is_zombie(self):
        return self.task_state() & self.TASK_ZOMBIE

    # This will be used eventually for live debugging
    def needs_update(self):
        return False

    def update_mem_usage(self):
        if self.mem_valid and self.needs_update():
            return

        if self.is_zombie() or self.is_exiting():
            return

        mm = self.task_struct['mm']
        if not mm:
            self.mem_valid = True
            return

        self.rss = self.get_rss()
        self.total_vm = long(mm['total_vm'])
        self.pgd = long(mm['pgd'])
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

    # This should be a function bounded to the crash.arch object used
    # for this session.  That's how we can get the appropriate arch
    # without needing to get it explicitly.
    def set_get_stack_pointer(self, fn):
        self.__class__.get_stack_pointer_fn = fn

    def get_stack_pointer(self):
        # This unbinds the function from the task object so we don't
        # pass self to the function.
        fn = self.get_stack_pointer_fn
        return fn(self.thread)

    def get_rss_field(self):
        return long(self.task_struct['mm']['rss'].value())

    def get__rss_field(self):
        return long(self.task_struct['mm']['_rss'].value())

    def get_rss_stat_field(self):
        stat = self.task_struct['mm']['rss_stat']['count']
        stat0 = self.task_struct['mm']['rss_stat']['count'][0]
        rss = 0
        for i in range(stat.type.sizeof / stat[0].type.sizeof):
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
    def which_get_rss(self):
        if 'rss' in self.mm_struct_fields:
            return self.__class__.get_rss_field
        elif '_rss' in self.mm_struct_fields:
            return self.__class__.get__rss_field
        elif 'rss_stat' in self.mm_struct_fields:
            self.__class__.MM_FILEPAGES = get_value('MM_FILEPAGES')
            self.__class__.MM_ANONPAGES = get_value('MM_ANONPAGES')
            return self.__class__.get_rss_stat_field
        elif '_anon_rss' in self.mm_struct_fields or \
             '_file_rss' in self.mm_struct_fields:
            self.__class__.atomic_long_type = gdb.lookup_type('atomic_long_t')
            return self.__class__.get_anon_file_rss_fields
        else:
            raise RuntimeError("No method to retrieve RSS from task found.")

    def last_run__last_run(self):
        return long(self.task_struct['last_run'])

    def last_run__last_run(self):
        return long(self.task_struct['timestamp'])

    def last_run__last_arrival(self):
        return long(self.task_struct['sched_info']['last_arrival'])

    def which_last_run(self):
        fields = self.task_struct_type.keys()
        if 'sched_info' in fields and \
           'last_arrival' in self.task_struct_type['sched_info'].type.keys():
           return self.__class__.last_run__last_arrival

        if 'last_run' in fields:
            return self.__class__.last_run__last_run

        if 'timestamp' in fields:
            return self.__class__.last_run__timestamp

        raise RuntimeError("No method to retrieve last run from task found.")
