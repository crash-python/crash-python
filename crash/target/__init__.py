# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Any, Iterator, List, Optional, Tuple, Type

import abc
import sys

import gdb

from crash.exceptions import MissingSymbolError
import crash.infra.callback

from crash.types.percpu import get_percpu_vars
from crash.util.symbols import Symbols, Symvals
from crash.util import get_typed_pointer

symbols = Symbols(['runqueues'])
symvals = Symvals(['crashing_cpu'])

class IncorrectTargetError(ValueError):
    """Incorrect target implementation for this kernel"""
    pass

PTID = Tuple[int, int, int]

# This keeps stack traces from continuing into userspace and causing problems.
class KernelFrameFilter:
    def __init__(self, address: int) -> None:
        self.name = "KernelFrameFilter"
        self.priority = 100
        self.enabled = True
        self.address = address
        gdb.frame_filters[self.name] = self

    def filter(self, frame_iter: Iterator[Any]) -> Any:
        return KernelAddressIterator(frame_iter, self.address)

class KernelAddressIterator:
    def __init__(self, ii: Iterator, address: int) -> None:
        self.input_iterator = ii
        self.address = address

    def __iter__(self) -> Any:
        return self

    def __next__(self) -> Any:
        frame = next(self.input_iterator)

        if frame.inferior_frame().pc() < self.address:
            raise StopIteration

        return frame

# A working target will be a mixin composed of a class derived from
# TargetBase and TargetFetchRegistersBase

class TargetBase(gdb.LinuxKernelTarget, metaclass=abc.ABCMeta):
    def __init__(self, debug: int = 0) -> None:
        super().__init__()

        self.debug = debug
        self.shortname = "Crash-Python Linux Target"
        self.longname = "Use a Core file as a Linux Kernel Target"
        self.ready = False

        self.crashing_thread: Optional[gdb.InferiorThread] = None

    def open(self, name: str, from_tty: bool) -> None:
        if not self.fetch_registers_usable():
            raise IncorrectTargetError("Not usable")

        if not gdb.objfiles()[0].has_symbols():
            raise ValueError("Cannot debug kernel without symbol table")

        super().open(name, from_tty)

        crash.infra.callback.target_ready()

        self.setup_tasks()

    def setup_tasks(self) -> None:
        # pylint complains about this.  It's ugly but putting the import within
        # setup_tasks breaks the cycle.
        # pylint: disable=cyclic-import
        from crash.types.task import LinuxTask, types as task_types
        import crash.cache.tasks # pylint: disable=redefined-outer-name
        print("Loading tasks...", end="")
        sys.stdout.flush()

        rqs = get_percpu_vars(symbols.runqueues)
        rqscurrs = {int(x["curr"]) : k for (k, x) in rqs.items()}

        task_count = 0
        try:
            crashing_cpu = symvals.crashing_cpu
        except MissingSymbolError:
            crashing_cpu = -1

        task_struct_p_type = task_types.task_struct_type.pointer()
        for thread in gdb.selected_inferior().threads():
            task_address = thread.ptid[2]

            task = get_typed_pointer(task_address, task_struct_p_type)
            ltask = LinuxTask(task.dereference())

            active = task_address in rqscurrs
            if active:
                cpu = rqscurrs[task_address]
                regs = self.kdumpfile.attr.cpu[cpu].reg
                ltask.set_active(cpu, regs)

            thread.info = ltask
            if active and cpu == crashing_cpu:
                self.crashing_thread = thread

            self.arch_setup_thread(thread)
            ltask.attach_thread(thread)

            crash.cache.tasks.cache_task(ltask)

            task_count += 1
            if task_count % 100 == 0:
                print(".", end='')
                sys.stdout.flush()
        print(" done. ({} tasks total)".format(task_count))

    def close(self) -> None:
        pass

    # pylint: disable=unused-argument
    def thread_alive(self, ptid: PTID) -> bool:
        return True

    # pylint: disable=unused-argument
    def prepare_to_store(self, thread: gdb.InferiorThread) -> None:
        pass

    @abc.abstractmethod
    def fetch_registers_usable(self) -> bool:
        pass

    @abc.abstractmethod
    def fetch_registers(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> Optional[gdb.RegisterCollectionType]:
        pass

    # pylint: disable=unused-argument
    def store_registers(self, thread: gdb.InferiorThread, registers: gdb.RegisterCollectionType) -> None:
        raise TypeError("This target is read-only.")

    # pylint: disable=unused-argument
    def has_execution(self, ptid: PTID) -> bool:
        return False

    @abc.abstractmethod
    def arch_setup_thread(self, thread: gdb.InferiorThread) -> None:
        pass

    @abc.abstractmethod
    def get_stack_pointer(self, thread: gdb.InferiorThread) -> int:
        pass

class TargetFetchRegistersBase(metaclass=abc.ABCMeta):
    """
    The base class from which to implement the fetch_registers callback.

    The architecture code must implement the :meth:`fetch_active` and
    :meth:`fetch_scheduled` methods.
    """
    _enabled: bool = False

    def __init__(self) -> None:
        super().__init__()
        self.fetching: bool = False

    # pylint: disable=unused-argument
    @classmethod
    def enable(cls, unused: Optional[gdb.Type] = None) -> None:
        cls._enabled = True

    @classmethod
    def fetch_registers_usable(cls) -> bool:
        return cls._enabled

    @abc.abstractmethod
    def fetch_active(self, thread: gdb.InferiorThread,
                     register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        pass

    @abc.abstractmethod
    def fetch_scheduled(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        pass

    def fetch_registers(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> Optional[gdb.RegisterCollectionType]:
        ret: Optional[gdb.RegisterCollectionType] = None

        # Don't recurse, but don't fail either
        if self.fetching:
            return None

        self.fetching = True
        try:
            if thread.info.active:
                ret = self.fetch_active(thread, register)
            else:
                ret = self.fetch_scheduled(thread, register)
        except AttributeError:
            # We still want to be able to list the threads even if we haven't
            # setup tasks.
            ret = None

        self.fetching = False
        return ret

_targets: List[Type[TargetBase]] = []
def register_target(new_target: Type[TargetBase]) -> None:
    _targets.append(new_target)

def setup_target() -> TargetBase:
    for target in _targets:
        t = None
        try:
            t = target()
            t.open("", False)
            return t
        except IncorrectTargetError:
            del t

    raise IncorrectTargetError("Could not identify target implementation for this kernel")

def check_target() -> TargetBase:
    target = gdb.current_target()

    if target is None:
        raise ValueError("No current target")

    if not isinstance(target, TargetBase):
        raise ValueError(f"Current target {type(target)} is not supported")

    return target
