# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
from typing import Tuple

import gdb

PTID = Tuple[int, int, int]

class TestTarget(gdb.Target):
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
                        register: gdb.Register) -> None:
        pass

    # pylint: disable=unused-argument
    def thread_alive(self, ptid: PTID) -> bool:
        return True

    def setup_task(self) -> None:
        ptid = (1, 1, 0)
        gdb.selected_inferior().new_thread(ptid, self)
