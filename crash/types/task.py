# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterator, Callable, Dict, List

import gdb

from crash.exceptions import InvalidArgumentError, ArgumentTypeError
from crash.exceptions import UnexpectedGDBTypeError, MissingFieldError
from crash.util import array_size, struct_has_member
from crash.util.symbols import Types, Symvals, SymbolCallbacks
from crash.types.list import list_for_each_entry

PF_EXITING = 0x4

types = Types(['struct task_struct', 'struct mm_struct', 'atomic_long_t'])
symvals = Symvals(['init_task', 'init_mm'])

# This is pretty painful.  These are all #defines so none of them end
# up with symbols in the kernel.  The best approximation we have is
# task_state_array which doesn't include all of them.  All we can do
# is make some assumptions based on the changes upstream.  This will
# be fragile.
class TaskStateFlags:
    """
    A class to contain state related to discovering task flag values.
    Not meant to be instantiated.


    The initial values below are overridden once symbols are available to
    resolve them properly.
    """
    TASK_RUNNING = 0

    TASK_FLAG_UNINITIALIZED = -1

    TASK_INTERRUPTIBLE: int = TASK_FLAG_UNINITIALIZED
    TASK_UNINTERRUPTIBLE: int = TASK_FLAG_UNINITIALIZED
    TASK_STOPPED: int = TASK_FLAG_UNINITIALIZED
    EXIT_ZOMBIE: int = TASK_FLAG_UNINITIALIZED
    TASK_DEAD: int = TASK_FLAG_UNINITIALIZED
    EXIT_DEAD: int = TASK_FLAG_UNINITIALIZED
    TASK_SWAPPING: int = TASK_FLAG_UNINITIALIZED
    TASK_TRACING_STOPPED: int = TASK_FLAG_UNINITIALIZED
    TASK_WAKEKILL: int = TASK_FLAG_UNINITIALIZED
    TASK_WAKING: int = TASK_FLAG_UNINITIALIZED
    TASK_PARKED: int = TASK_FLAG_UNINITIALIZED
    __TASK_IDLE: int = TASK_FLAG_UNINITIALIZED

    TASK_NOLOAD: int = TASK_FLAG_UNINITIALIZED
    TASK_NEW: int = TASK_FLAG_UNINITIALIZED
    TASK_IDLE: int = TASK_FLAG_UNINITIALIZED

    _state_field: str = 'state'

    def __init__(self) -> None:
        raise NotImplementedError("This class is not meant to be instantiated")

    @classmethod
    def has_flag(cls, flagname: str) -> bool:
        v = getattr(cls, flagname)
        return v != cls.TASK_FLAG_UNINITIALIZED

    @classmethod
    def task_state_flags_callback(cls, symbol: gdb.Symbol) -> None:
        # pylint: disable=unused-argument
        """
        Detect which task flags this kernel uses.

        Meant to be used as a SymbolCallback.

        Different kernels use different task flags or even different values
        for the same flags.  This method tries to determine the flags for
        the kernel.

        Args:
            symbol: The ``task_state_array`` symbol.
        """
        task_state_array = symbol.value()
        count = array_size(task_state_array)

        bit = 0
        for i in range(count):
            state = task_state_array[i].string()
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

            assert cls.TASK_PARKED == 0x0040
            assert cls.TASK_DEAD == 0x0080
            assert cls.TASK_WAKEKILL == 0x0100
            assert cls.TASK_WAKING == 0x0200

        # Linux 3.14 removed several elements from task_state_array
        # so we'll have to make some assumptions.
        # TASK_NOLOAD wasn't introduced until 4.2 and wasn't added
        # to task_state_array until v4.14.  There's no way to
        # detect whether the use of the flag is valid for a particular
        # kernel release.
        elif cls.has_flag('EXIT_DEAD'):
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

            assert cls.TASK_DEAD == 0x0040
            assert cls.TASK_WAKEKILL == 0x0080
            assert cls.TASK_WAKING == 0x0100
            assert cls.TASK_PARKED == 0x0200
        else:
            assert cls.TASK_DEAD == 64
            assert cls.TASK_WAKEKILL == 128
            assert cls.TASK_WAKING == 256
            assert cls.TASK_PARKED == 512

        if cls.has_flag('TASK_NOLOAD'):
            assert cls.TASK_NOLOAD == 1024
            cls.TASK_IDLE = cls.TASK_NOLOAD | cls.TASK_UNINTERRUPTIBLE
            assert cls.TASK_IDLE == 1026
        if cls.has_flag('TASK_NEW'):
            assert cls.TASK_NEW == 2048

        cls._check_state_bits()

    @classmethod
    def _check_state_bits(cls) -> None:
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

        if missing:
            raise RuntimeError("Missing required task states: {}"
                               .format(",".join(missing)))

symbol_cbs = SymbolCallbacks([('task_state_array',
                               TaskStateFlags.task_state_flags_callback)])

TF = TaskStateFlags

class LinuxTask:
    """
    A wrapper class for ``struct task_struct``.  There will be typically
    one of these allocated for every task discovered in the debugging
    environment.

    Args:
        task_struct: The task to wrap.  The value must be of type
            ``struct task_struct``.

    Attributes:
        task_struct (:obj:`gdb.Value`): The task being wrapped.  The value
            is of type ``struct task_struct``.
        active (:obj:`bool`): Whether this task is active
        cpu (:obj:`int`): The CPU number the task was using
        regs: The registers associated with this task, if active
        thread_info (:obj:`gdb.Value`): The architecture-specific
            ``struct thread_info`` for this task.  The value will be of
            type ``struct thread_info``.
        thread (:obj:`gdb.InferiorThread`): The GDB representation of the
            thread.
        mem_valid (:obj:`bool`): Whether the memory statistics are currently
            valid.
        rss (:obj:`int`): The size of the resident memory for this task.
        total_vm (:obj:`int`): The total size of the vm space for this task.
        pgd_addr (:obj:`int`): The address of the top of the page table tree.

    Raises:
        :obj:`.ArgumentTypeError`: task_struct was not a :obj:`gdb.Value`.
        :obj:`.UnexpectedGDBTypeError`: task_struct was not of type
            ``struct task_struct``.
        :obj:`.InvalidArgumentError`: The cpu number was not ``None`` or an
            :obj:`int`.
    """
    _valid = False
    _task_state_has_exit_state = None
    _anon_file_rss_fields: List[str] = list()

    # Version-specific hooks -- these will be None here but we'll raise a
    # NotImplementedError if any of them aren't found.
    _get_rss: Callable[['LinuxTask'], int]
    _get_last_run: Callable[['LinuxTask'], int]

    _state_field: str

    def __init__(self, task_struct: gdb.Value) -> None:
        self._init_task_types(task_struct)

        if not isinstance(task_struct, gdb.Value):
            raise ArgumentTypeError('task_struct', task_struct, gdb.Value)

        if not (task_struct.type == types.task_struct_type or
                task_struct.type == types.task_struct_type.pointer()):
            raise UnexpectedGDBTypeError('task_struct', task_struct,
                                         types.task_struct_type)

        self.task_struct = task_struct
        self.active = False
        self.cpu = -1
        self.regs: Dict[str, int] = dict()

        self.thread_info: gdb.Value
        self.thread: gdb.InferiorThread

        # mem data
        self.mem_valid = False
        self.rss = 0
        self.total_vm = 0
        self.pgd_addr = 0

    @classmethod
    def _init_task_types(cls, task: gdb.Value) -> None:
        if not cls._valid:
            t = types.task_struct_type
            if task.type != t:
                raise UnexpectedGDBTypeError('task', task, t)

            # Using a type within the same context makes things a *lot* faster
            # This works around a shortcoming in gdb.  A type lookup and
            # a type resolved from a symbol will be different structures
            # within gdb.  Equality requires a deep comparison rather than
            # a simple pointer comparison.
            types.override('struct task_struct', task.type)
            fields = [x.name for x in types.task_struct_type.fields()]
            cls._task_state_has_exit_state = 'exit_state' in fields
            if 'state' in fields:
                cls._state_field = 'state'
            elif '__state' in fields:
                cls._state_field = '__state'
            else:
                raise MissingFieldError("No way to resolve task_struct.state")

            cls._pick_get_rss()
            cls._pick_last_run()
            cls._valid = True

    def set_active(self, cpu: int, regs: Dict[str, int]) -> None:
        """
        Set this task as active in the debugging environment

        Args:
            cpu: Which CPU this task was using
            regs: The registers associated with this task

        Raises:
            :obj:`.InvalidArgumentError`: The cpu was not a valid integer.
        """
        if not (isinstance(cpu, int) and cpu >= 0):
            raise InvalidArgumentError("cpu must be integer >= 0")

        self.active = True
        self.cpu = cpu
        self.regs = regs

    def attach_thread(self, thread: gdb.InferiorThread) -> None:
        """
        Associate a gdb thread with this task

        Args:
            thread: The gdb thread to associate with this task
        """
        if not isinstance(thread, gdb.InferiorThread):
            raise TypeError("Expected gdb.InferiorThread")
        self.thread = thread

    def set_thread_info(self, thread_info: gdb.Value) -> None:
        """
        Set the thread info for this task

        The thread info structure is architecture specific.  This method
        allows the architecture code to assign its thread info structure
        to this task.

        Args:
            thread_info: The ``struct thread_info`` to be associated with
                this task.  The value must be of type ``struct thread_info``.
        """
        self.thread_info = thread_info

    def get_thread_info(self) -> gdb.Value:
        """
        Get the thread info for this task

        The thread info structure is architecture specific and so this
        method abstracts its retreival.

        Returns:
            :obj:`gdb.Value`: The struct thread_info associated with this
                task.  The type of the value is ``struct thread_info``.
        """
        return self.thread_info

    def get_last_cpu(self) -> int:
        """
        Returns the last cpu this task was scheduled to execute on

        Returns:
            :obj:`int`: The last cpu this task was scheduled to execute on
        """
        if struct_has_member(self.task_struct, 'cpu'):
            cpu = self.task_struct['cpu']
        else:
            cpu = self.thread_info['cpu']
        return int(cpu)

    # Hrm.  This seems broken since we're combining flags from
    # two fields.
    def task_state(self) -> int:
        """
        Return the task state flags for this task *(possibly broken due to
        combining flags from ``state`` and ``exit_state``)*.

        Returns:
            :obj:`int`: The state flags for this task.
        """
        state = int(self.task_struct[self._state_field])
        if self._task_state_has_exit_state:
            state |= int(self.task_struct['exit_state'])
        return state

    def maybe_dead(self) -> bool:
        """
        Returns whether this task is dead

        Returns:
            :obj:`bool`: Whether this task is dead
        """
        state = self.task_state()

        known = TF.TASK_INTERRUPTIBLE
        known |= TF.TASK_UNINTERRUPTIBLE
        known |= TF.EXIT_ZOMBIE
        known |= TF.TASK_STOPPED

        if TF.has_flag('TASK_SWAPPING'):
            known |= TF.TASK_SWAPPING
        return (state & known) == 0

    def task_flags(self) -> int:
        """
        Returns the flags for this task

        Returns:
            :obj:`int`: The flags for this task
        """
        return int(self.task_struct['flags'])

    def is_exiting(self) -> bool:
        """
        Returns whether a task is exiting

        Returns:
            :obj:`bool`: Whether the task is exiting
        """
        return (self.task_flags() & PF_EXITING) != 0

    def is_zombie(self) -> bool:
        """
        Returns whether a task is in Zombie state

        Returns:
            :obj:`bool`: Whether the task is in zombie state
        """
        return (self.task_state() & TF.EXIT_ZOMBIE) != 0

    def is_thread_group_leader(self) -> bool:
        """
        Returns whether a task is a thread group leader

        Returns:
            :obj:`bool`: Whether the task is a thread group leader
        """
        return int(self.task_struct['exit_signal']) >= 0

    def update_mem_usage(self) -> None:
        """
        Update the memory usage for this task

        Tasks are created initially without their memory statistics.  This
        method explicitly updates them.
        """
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

    def task_name(self, brackets: bool = False) -> str:
        """
        Returns the ``comm`` field of this task

        Args:
            brackets: If this task is a kernel thread, surround the name
                in square brackets

        Returns:
            :obj:`str`: The ``comm`` field of this task a python string
        """
        name = self.task_struct['comm'].string()
        if brackets and self.is_kernel_task():
            return f"[{name}]"
        return name

    def task_pid(self) -> int:
        """
        Returns the pid of this task

        Returns:
            :obj:`int`: The pid of this task
        """
        return int(self.task_struct['pid'])

    def parent_pid(self) -> int:
        """
        Returns the pid of this task's parent

        Returns:
            :obj:`int`: The pid of this task's parent
        """
        return int(self.task_struct['parent']['pid'])

    def task_address(self) -> int:
        """
        Returns the address of the task_struct for this task

        Returns:
            :obj:`int`: The address of the task_struct
        """
        return int(self.task_struct.address)

    def is_kernel_task(self) -> bool:
        if self.task_struct['pid'] == 0:
            return True

        if self.is_zombie() or self.is_exiting():
            return False

        mm = self.task_struct['mm']
        if mm == 0:
            return True

        if symvals.init_mm and mm == symvals.init_mm.address:
            return True

        return False

    @classmethod
    def set_get_stack_pointer(cls, fn: Callable[[gdb.Value], int]) -> None:
        """
        Set the stack pointer callback for this architecture

        The callback must accept a :obj:`gdb.Value` of type
        ``struct thread`` and return a :obj:`int` containing the address
        of the stack pointer.

        Args:
            fn: The callback to use.  It will be used by all tasks.
        """
        setattr(cls, '_get_stack_pointer_fn', fn)

    def get_stack_pointer(self) -> int:
        """
        Get the stack pointer for this task

        Returns:
            :obj:`int`: The address of the stack pointer for this task.

        Raises:
            :obj:`NotImplementedError`: The architecture hasn't provided
            a stack pointer callback.
        """
        try:
            fn = getattr(self, '_get_stack_pointer_fn')
        except AttributeError:
            raise NotImplementedError("Architecture hasn't provided stack pointer callback") from None

        return fn(self.task_struct['thread'])

    def _get_rss_field(self) -> int:
        return int(self.task_struct['mm']['rss'].value())

    def _get__rss_field(self) -> int:
        return int(self.task_struct['mm']['_rss'].value())

    def _get_rss_stat_field(self) -> int:
        stat = self.task_struct['mm']['rss_stat']['count']
        rss = 0
        for i in range(array_size(stat)):
            rss += int(stat[i]['counter'])
        return rss

    def _get_anon_file_rss_fields(self) -> int:
        mm = self.task_struct['mm']
        rss = 0
        for name in self._anon_file_rss_fields:
            if mm[name].type == types.atomic_long_t_type:
                rss += int(mm[name]['counter'])
            else:
                rss += int(mm[name])
        return rss

    # The Pythonic way to do this is by generating the LinuxTask class
    # dynamically.  We may do that eventually, but for now we can just
    # select the proper function and assign it to the class.
    @classmethod
    def _pick_get_rss(cls) -> None:
        if struct_has_member(types.mm_struct_type, 'rss'):
            cls._get_rss = cls._get_rss_field
        elif struct_has_member(types.mm_struct_type, '_rss'):
            cls._get_rss = cls._get__rss_field
        elif struct_has_member(types.mm_struct_type, 'rss_stat'):
            cls._get_rss = cls._get_rss_stat_field
        else:
            if struct_has_member(types.mm_struct_type, '_file_rss'):
                cls._anon_file_rss_fields.append('_file_rss')

            if struct_has_member(types.mm_struct_type, '_anon_rss'):
                cls._anon_file_rss_fields.append('_anon_rss')

            cls._get_rss = cls._get_anon_file_rss_fields

            if not cls._anon_file_rss_fields:
                raise RuntimeError("No method to retrieve RSS from task found.")

    def __get_rss(self) -> int:
        raise NotImplementedError("_get_rss not implemented")

    def get_rss(self) -> int:
        """
        Return the resident set for this task

        Returns:
            :obj:`int`: The size of the resident memory set for this task
        """
        return self._get_rss()

    def _last_run__last_run(self) -> int:
        return int(self.task_struct['last_run'])

    def _last_run__timestamp(self) -> int:
        return int(self.task_struct['timestamp'])

    def _last_run__last_arrival(self) -> int:
        return int(self.task_struct['sched_info']['last_arrival'])

    @classmethod
    def _pick_last_run(cls) -> None:
        fields = types.task_struct_type.keys()
        if ('sched_info' in fields and
                'last_arrival' in types.task_struct_type['sched_info'].type.keys()):
            cls._get_last_run = cls._last_run__last_arrival

        elif 'last_run' in fields:
            cls._get_last_run = cls._last_run__last_run

        elif 'timestamp' in fields:
            cls._get_last_run = cls._last_run__timestamp
        else:
            raise RuntimeError("No method to retrieve last run from task found.")

    def last_run(self) -> int:
        """
        The timestamp of when this task was last run

        Returns:
            :obj:`int`: The timestamp of when this task was last run
        """
        return self._get_last_run()

def for_each_thread_group_leader() -> Iterator[gdb.Value]:
    """
    Iterate the task list and yield each thread group leader

    Yields:
        :obj:`gdb.Value`: The next task on the list.  The value is of
        type ``struct task_struct``.
    """
    task_list = symvals.init_task['tasks']
    for task in list_for_each_entry(task_list, symvals.init_task.type,
                                    'tasks', include_head=True):
        yield task

def for_each_thread_in_group(task: gdb.Value) -> Iterator[gdb.Value]:
    """
    Iterate a thread group leader's thread list and
    yield each struct task_struct

    Args:
        task: The task_struct that is the thread group leader.  The value
            must be of type ``struct task_struct``.

    Yields:
        :obj:`gdb.Value`: The next task on the list.  The value is of type
        ``struct task_struct``.
    """
    thread_list = task['thread_group']
    for thread in list_for_each_entry(thread_list, symvals.init_task.type,
                                      'thread_group'):
        yield thread

def for_each_all_tasks() -> Iterator[gdb.Value]:
    """
    Iterate the task list and yield each task including any associated
    thread tasks

    Yields:
        :obj:`gdb.Value`: The next task on the list.  The value is of type
        ``struct task_struct``.
    """
    for leader in for_each_thread_group_leader():
        yield leader
        for task in for_each_thread_in_group(leader):
            yield task
