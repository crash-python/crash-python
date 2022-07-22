# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Tuple, Callable, Optional

import sys
import shlex

from kdumpfile import kdumpfile, KDUMP_KVADDR
from kdumpfile.exceptions import AddressTranslationException, EOFException
from kdumpfile.exceptions import NoDataException
import addrxlat.exceptions

import gdb

FetchRegistersCallbackType = Callable[[gdb.InferiorThread, Optional[gdb.RegisterDescriptor]],
                                      gdb.RegisterCollectionType]
StoreRegistersCallbackType = Callable[[gdb.InferiorThread, gdb.RegisterCollectionType], None]

PTID = Tuple[int, int, int]

class Target(gdb.LinuxKernelTarget):

    _fetch_registers: FetchRegistersCallbackType

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.debug = debug
        self.shortname = "kdumpfile"
        self.longname = "Use a Linux kernel kdump file as a target"

        self.register()

    def open(self, name: str, from_tty: bool) -> None:
        print("Opened kdump.Target")

    def close(self) -> None:
        try:
            self.unregister()
        except RuntimeError:
            pass

    # pylint: disable=unused-argument
    def thread_alive(self, ptid: PTID) -> bool:
        return True

    def pid_to_str(self, ptid: PTID) -> str:
        return "pid {:d}".format(ptid[1])

    def set_fetch_registers(self, callback: FetchRegistersCallbackType) -> None:
        self._fetch_registers = callback # type: ignore

    def fetch_registers(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> gdb.RegisterCollectionType:
        try:
            return self._fetch_registers(thread, register) # type: ignore
        except AttributeError as e:
            raise NotImplementedError(f"Target did not define fetch_registers callback: {e}") from e

    def prepare_to_store(self, thread: gdb.InferiorThread) -> None:
        pass

    # We don't need to store anything; The regcache is already written.
    # pylint: disable=unused-argument
    def store_registers(self, thread: gdb.InferiorThread,
                        register: gdb.RegisterCollectionType) -> None:
        pass

    # pylint: disable=unused-argument
    def has_execution(self, ptid: PTID) -> bool:
        return False
