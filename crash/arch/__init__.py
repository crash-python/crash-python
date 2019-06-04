# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import List, Iterator, Any, Optional, Type

import gdb
from gdb.FrameDecorator import FrameDecorator

class CrashArchitecture(object):
    ident = "base-class"
    aliases: List[str] = list()
    def __init__(self) -> None:
        pass

    def fetch_register_active(self, thread: gdb.InferiorThread,
                              register: int) -> None:
        raise NotImplementedError("setup_thread_active not implemented")

    def fetch_register_scheduled(self, thread: gdb.InferiorThread,
                                 register: int) -> None:
        raise NotImplementedError("setup_thread_scheduled not implemented")

    def setup_thread_info(self, thread: gdb.InferiorThread) -> None:
        raise NotImplementedError("setup_thread_info not implemented")

    def fetch_register(self, thread: gdb.InferiorThread, register: int) -> None:
        if thread.info.active:
            self.fetch_register_active(thread, register)
        else:
            self.fetch_register_scheduled(thread, register)

    def get_stack_pointer(self, thread_struct: gdb.Value) -> gdb.Value:
        raise NotImplementedError("get_stack_pointer is not implemented")

# This keeps stack traces from continuing into userspace and causing problems.
class KernelFrameFilter(object):
    def __init__(self, address: int) -> None:
        self.name = "KernelFrameFilter"
        self.priority = 100
        self.enabled = True
        self.address = address
        gdb.frame_filters[self.name] = self

    def filter(self, frame_iter: Iterator[FrameDecorator]) -> Any:
        return KernelAddressIterator(frame_iter, self.address)

class KernelAddressIterator(object):
    def __init__(self, ii: Iterator[gdb.Frame], address: int) -> None:
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
