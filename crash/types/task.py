# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.util import array_size, struct_has_member
from crash.util.symbols import Types, Symvals, SymbolCallbacks
from crash.types.list import list_for_each_entry

PF_EXITING = 0x4

def get_value(symname):
    sym = gdb.lookup_symbol(symname, block=None, domain=gdb.SYMBOL_VAR_DOMAIN)
    if sym[0]:
        return sym[0].value()

types = Types(['struct task_struct', 'struct mm_struct', 'atomic_long_t' ])
symvals = Symvals([ 'task_state_array', 'init_task' ])

# This is pretty painful.  These are all #defines so none of them end
# up with symbols in the kernel.  The best approximation we have is
# task_state_array which doesn't include all of them.  All we can do
# is make some assumptions based on the changes upstream.  This will
# be fragile.
class TaskStateFlags(object):
    TASK_RUNNING = 0

    TASK_FLAG_UNINITIALIZED = -1

    TASK_INTERRUPTIBLE: int=TASK_FLAG_UNINITIALIZED
    TASK_UNINTERRUPTIBLE: int=TASK_FLAG_UNINITIALIZED
    TASK_STOPPED: int=TASK_FLAG_UNINITIALIZED
    EXIT_ZOMBIE: int=TASK_FLAG_UNINITIALIZED
    TASK_DEAD: int=TASK_FLAG_UNINITIALIZED
    EXIT_DEAD: int=TASK_FLAG_UNINITIALIZED
    TASK_SWAPPING: int=TASK_FLAG_UNINITIALIZED
    TASK_TRACING_STOPPED: int=TASK_FLAG_UNINITIALIZED
    TASK_WAKEKILL: int=TASK_FLAG_UNINITIALIZED
    TASK_WAKING: int=TASK_FLAG_UNINITIALIZED
    TASK_PARKED: int=TASK_FLAG_UNINITIALIZED
    __TASK_IDLE: int=TASK_FLAG_UNINITIALIZED

    TASK_NOLOAD: int=TASK_FLAG_UNINITIALIZED
    TASK_NEW: int=TASK_FLAG_UNINITIALIZED
    TASK_IDLE: int=TASK_FLAG_UNINITIALIZED

    @classmethod
    def has_flag(cls, flagname):
        v = getattr(cls, flagname)
        return v != cls.TASK_FLAG_UNINITIALIZED

    @classmethod
    def _task_state_flags_callback(cls, symbol):
        count = array_size(symvals.task_state_array)

        bit = 0
        for i in range(count):
            state = symvals.task_state_array[i].string()
            state_strings = {
                '(running)'      : 'TASK_RUNNING',
                '(sleeping)'     : 'TASK_INTERRUPTIBLE',
                '(disk sleep)'   : 'TASK_UNINTERRUPTIBLE',
                '(stopped)'      : 'TASK_STOPPED',
                '(zombie)'       : 'EXIT_ZOMBIE',
                'x (dead)'       : 'TASK_DEAD',
                'X (dead)'       : 'EXIT_DEAD',
                '(swapping)'     : 'TASK_SWAPPING',
                '(tracing stop)' : 'TASK_TRACING_STOPPED',
                '(wakekill)'     : 'TASK_WAKEKILL',
                '(waking)'       : 'TASK_WAKING',
                '(parked)'       : 'TASK_PARKED',
                '(idle)'         : '__TASK_IDLE',
            }

            for key in state_strings:
                if key in state:
                    setattr(cls, state_strings[key], bit)

            if bit == 0:
                bit = 1
            else:
                bit <<= 1

        # Linux 4.14 re-introduced TASK_PARKED into task_state_array
        # which renumbered some bits
        if cls.has_flag('TASK_PARKED') and not cls.has_flag('TASK_DEAD'):
            newbits = cls.TASK_PARKED << 1
            cls.TASK_DEAD = newbits
            cls.TASK_WAKEKILL = newbits << 1
            cls.TASK_WAKING = newbits << 2
            cls.TASK_NOLOAD = newbits << 3
            cls.TASK_NEW = newbits << 4

            assert(cls.TASK_PARKED   == 0x0040)
            assert(cls.TASK_DEAD     == 0x0080)
            assert(cls.TASK_WAKEKILL == 0x0100)
            assert(cls.TASK_WAKING   == 0x0200)

        # Linux 3.14 removed several elements from task_state_array
        # so we'll have to make some assumptions.
        # TASK_NOLOAD wasn't introduced until 4.2 and wasn't added
        # to task_state_array until v4.14.  There's no way to
        # detect whether the use of the flag is valid for a particular
        # kernel release.
        elif cls.has_flag('TASK_DEAD'):
            if cls.EXIT_ZOMBIE > cls.EXIT_DEAD:
                newbits = cls.EXIT_ZOMBIE << 1
            else:
                newbits = cls.EXIT_DEAD << 1
            cls.TASK_DEAD = newbits
            cls.TASK_WAKEKILL = newbits << 1
            cls.TASK_WAKING = newbits << 2
            cls.TASK_PARKED = newbits << 3
            cls.TASK_NOLOAD = newbits << 4
            cls.TASK_NEW = newbits << 5

            assert(cls.TASK_DEAD     == 0x0040)
            assert(cls.TASK_WAKEKILL == 0x0080)
            assert(cls.TASK_WAKING   == 0x0100)
            assert(cls.TASK_PARKED   == 0x0200)
        else:
            assert(cls.TASK_DEAD     == 64)
            assert(cls.TASK_WAKEKILL == 128)
            assert(cls.TASK_WAKING   == 256)
            assert(cls.TASK_PARKED   == 512)

        if cls.has_flag('TASK_NOLOAD'):
            assert(cls.TASK_NOLOAD == 1024)
            cls.TASK_IDLE = cls.TASK_NOLOAD | cls.TASK_UNINTERRUPTIBLE
            assert(cls.TASK_IDLE == 1026)
        if cls.has_flag('TASK_NEW'):
            assert(cls.TASK_NEW == 2048)

        cls._check_state_bits()

    @classmethod
    def _check_state_bits(cls):
        required = [
            'TASK_RUNNING',
            'TASK_INTERRUPTIBLE',
            'TASK_UNINTERRUPTIBLE',
            'EXIT_ZOMBIE',
            'TASK_STOPPED',
        ]

        missing = []

        for bit in required:
            if not cls.has_flag(bit):
                missing.append(bit)

        if len(missing):
            raise RuntimeError("Missing required task states: {}"
                               .format(",".join(missing)))

symbol_cbs = SymbolCallbacks([ ('task_state_array',
                                TaskStateFlags._task_state_flags_callback) ])

TF = TaskStateFlags

class BadTaskError(TypeError):
    msgtemplate = "task_struct must be gdb.Value describing struct task_struct not {}"
    def __init__(self, task):
        if isinstance(task, gdb.Value):
            typedesc = task.type
        else:
            typedesc = type(task)
        super().__init__(self.msgtemplate.format(typedesc))

class LinuxTask(object):
    task_struct_type = None
    mm_struct_fields = None
    get_rss = None
    get_stack_pointer_fn = None
    valid = False

    def __init__(self, task_struct, active=False, cpu=None, regs=None):
        self.init_task_types(task_struct)

        if cpu is not None and not isinstance(cpu, int):
            raise TypeError("cpu must be integer or None")

        if not (isinstance(task_struct, gdb.Value) and
                (task_struct.type == types.task_struct_type or
                 task_struct.type == types.task_struct_type.pointer())):
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
            t = types.task_struct_type
            if task.type != t:
                raise BadTaskError(task)

            # Using a type within the same context makes things a *lot* faster
            # This works around a shortcoming in gdb.  A type lookup and
            # a type resolved from a symbol will be different structures
            # within gdb.  Equality requires a deep comparison rather than
            # a simple pointer comparison.
            types.task_struct_type = task.type
            fields = types.task_struct_type.fields()
            cls.task_state_has_exit_state = 'exit_state' in fields
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

    def get_last_cpu(self):
        try:
            return int(self.task_struct['cpu'])
        except gdb.error as e:
            return int(self.thread_info['cpu'])

    def task_state(self):
        state = int(self.task_struct['state'])
        if self.task_state_has_exit_state:
            state |= int(self.task_struct['exit_state'])
        return state

    def maybe_dead(self):
        state = self.task_state()

        known = TF.TASK_INTERRUPTIBLE
        known |= TF.TASK_UNINTERRUPTIBLE
        known |= TF.EXIT_ZOMBIE
        known |= TF.TASK_STOPPED

        if TF.has_flag('TASK_SWAPPING'):
            known |= TF.TASK_SWAPPING
        return (state & known) == 0

    def task_flags(self):
        return int(self.task_struct['flags'])

    def is_exiting(self):
        return self.task_flags() & PF_EXITING

    def is_zombie(self):
        return self.task_state() & TF.EXIT_ZOMBIE

    def is_thread_group_leader(self):
        return int(self.task_struct['exit_signal']) >= 0

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
        self.total_vm = int(mm['total_vm'])
        self.pgd_addr = int(mm['pgd'])
        self.mem_valid = True

    def task_name(self, brackets=False):
        name = self.task_struct['comm'].string()
        if brackets and self.is_kernel_task():
            return f"[{name}]"
        else:
            return name

    def task_pid(self):
        return int(self.task_struct['pid'])

    def parent_pid(self):
        return int(self.task_struct['parent']['pid'])

    def task_address(self):
        return int(self.task_struct.address)

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

    def get_stack_pointer(self):
        return self.get_stack_pointer_fn(self.task_struct['thread'])

    def get_rss_field(self):
        return int(self.task_struct['mm']['rss'].value())

    def get__rss_field(self):
        return int(self.task_struct['mm']['_rss'].value())

    def get_rss_stat_field(self):
        stat = self.task_struct['mm']['rss_stat']['count']
        stat0 = self.task_struct['mm']['rss_stat']['count'][0]
        rss = 0
        for i in range(stat.type.sizeof // stat[0].type.sizeof):
            rss += int(stat[i]['counter'])
        return rss

    def get_anon_file_rss_fields(self):
        mm = self.task_struct['mm']
        rss = 0
        for name in cls.anon_file_rss_fields:
            if mm[name].type == self.atomic_long_type:
                rss += int(mm[name]['counter'])
            else:
                rss += int(mm[name])
        return rss

    # The Pythonic way to do this is by generating the LinuxTask class
    # dynamically.  We may do that eventually, but for now we can just
    # select the proper function and assign it to the class.
    @classmethod
    def pick_get_rss(cls):
        if struct_has_member(types.mm_struct_type, 'rss'):
            cls.get_rss = cls.get_rss_field
        elif struct_has_member(types.mm_struct_type, '_rss'):
            cls.get_rss = cls.get__rss_field
        elif struct_has_member(types.mm_struct_type, 'rss_stat'):
            cls.MM_FILEPAGES = get_value('MM_FILEPAGES')
            cls.MM_ANONPAGES = get_value('MM_ANONPAGES')
            cls.get_rss = cls.get_rss_stat_field
        else:
            cls.anon_file_rss_fields = []

            if struct_has_member(types.mm_struct_type, '_file_rss'):
                cls.anon_file_rss_fields.append('_file_rss')

            if struct_has_member(types.mm_struct_type, '_anon_rss'):
                cls.anon_file_rss_fields.append('_anon_rss')

            cls.atomic_long_type = gdb.lookup_type('atomic_long_t')
            cls.get_rss = cls.get_anon_file_rss_fields

            if len(cls.anon_file_rss_fields):
                raise RuntimeError("No method to retrieve RSS from task found.")

    def last_run__last_run(self):
        return int(self.task_struct['last_run'])

    def last_run__timestamp(self):
        return int(self.task_struct['timestamp'])

    def last_run__last_arrival(self):
        return int(self.task_struct['sched_info']['last_arrival'])

    @classmethod
    def pick_last_run(cls):
        fields = types.task_struct_type.keys()
        if ('sched_info' in fields and
                'last_arrival' in types.task_struct_type['sched_info'].type.keys()):
            cls.last_run = cls.last_run__last_arrival

        elif 'last_run' in fields:
            cls.last_run = cls.last_run__last_run

        elif 'timestamp' in fields:
            cls.last_run = cls.last_run__timestamp
        else:
            raise RuntimeError("No method to retrieve last run from task found.")

def for_each_thread_group_leader():
    task_list = symvals.init_task['tasks']
    for task in list_for_each_entry(task_list, symvals.init_task.type,
                                     'tasks', include_head=True):
        yield task

def for_each_thread_in_group(task):
    thread_list = task['thread_group']
    for thread in list_for_each_entry(thread_list, symvals.init_task.type,
                                      'thread_group'):
        yield thread

def for_each_all_tasks():
    for leader in for_each_thread_group_leader():
        yield leader
        for task in for_each_thread_in_group(leader):
            yield task
