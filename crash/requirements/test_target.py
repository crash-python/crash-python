# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
from typing import Optional, Tuple

import gdb

PTID = Tuple[int, int, int]

class TestTarget(gdb.LinuxKernelTarget):
    def __init__(self) -> None:
        super().__init__()

        self.shortname = "testtarget"
        self.longname = "Target to test Target compatibility"
        self.register()

    def open(self, args: str, from_tty: bool) -> None:
        pass

    def close(self) -> None:
        pass

    def fetch_registers(self, thread: gdb.InferiorThread,
                        register: Optional[gdb.RegisterDescriptor]) -> Optional[gdb.RegisterCollectionType]:
        pass

    # pylint: disable=unused-argument
    def thread_alive(self, ptid: PTID) -> bool:
        return True
