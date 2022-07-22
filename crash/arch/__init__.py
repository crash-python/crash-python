# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import List, Iterator, Any, Optional, Type

import gdb
from gdb import RegisterNameType, RegisterCollectionType
from gdb import FetchRegistersCallbackType
from gdb.FrameDecorator import FrameDecorator

import crash

class FetchRegistersCallback:
    """
    The base class from which to implement the fetch_registers callback.

    The architecture code must implement the :meth:`fetch_active` and
    :meth:`fetch_scheduled` methods.
    """
    def fetch_active(self, thread: gdb.InferiorThread,
                     register: RegisterNameType) -> RegisterCollectionType:
        raise NotImplementedError("Target has no fetch_active callback")

    def fetch_scheduled(self, thread: gdb.InferiorThread,
                        register: RegisterNameType) -> RegisterCollectionType:
        raise NotImplementedError("Target has no fetch_scheduled callback")

    def __call__(self, thread: gdb.InferiorThread,
                 register: RegisterNameType) -> RegisterCollectionType:

        if thread.info.active:
            return self.fetch_active(thread, register)

        return self.fetch_scheduled(thread, register)

class CrashArchitecture:
    ident = "base-class"
    aliases: List[str] = list()

    _fetch_registers: FetchRegistersCallbackType

    def __init__(self) -> None:
        target = gdb.current_target()
        if target is None:
            raise ValueError("No target loaded") from None
        if not isinstance(target, gdb.LinuxKernelTarget):
            raise ValueError("Incorrect target loaded") from None

        try:
            target.set_fetch_registers(self._fetch_registers())
        except AttributeError:
            raise NotImplementedError("No fetch_registers callback defined") from None

    @classmethod
    def set_fetch_registers(cls, callback: FetchRegistersCallbackType) -> None:
        """
        Set a fetch_regisers callback for the Target to use.

        Args:
            callback: A Callable that accepts a :obj:`gdb.InferiorThread` and
                :obj:`gdb.Register` and populates the requested registers for
                the specified thread.  A register with the seemingly invalid
                register number of -1 is a request to populate all registers.
        """
        cls._fetch_registers = callback

    def setup_thread_info(self, thread: gdb.InferiorThread) -> None:
        raise NotImplementedError("setup_thread_info not implemented")

    def get_stack_pointer(self, thread_struct: gdb.Value) -> int:
        raise NotImplementedError("get_stack_pointer is not implemented")

    def setup_scheduled_frame_offset(self, task: gdb.Value) -> None:
        pass

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

architectures = {}
def register_arch(arch: Type[CrashArchitecture]) -> None:
    architectures[arch.ident] = arch
    for ident in arch.aliases:
        architectures[ident] = arch

def get_architecture(archname: str) -> Type[CrashArchitecture]:
    if archname in architectures:
        return architectures[archname]
    raise RuntimeError(f"Couldn't locate helpers for arch: {archname}")
