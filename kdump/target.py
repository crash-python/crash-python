# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Tuple, Callable

import sys
import shlex

from kdumpfile import kdumpfile, KDUMP_KVADDR
from kdumpfile.exceptions import AddressTranslationException, EOFException
from kdumpfile.exceptions import NoDataException
import addrxlat.exceptions

import gdb

TargetFetchRegisters = Callable[[gdb.InferiorThread, gdb.Register], None]

PTID = Tuple[int, int, int]

class Target(gdb.Target):

    _fetch_registers: TargetFetchRegisters

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.debug = debug
        self.shortname = "kdumpfile"
        self.longname = "Use a Linux kernel kdump file as a target"
        self.kdump: kdumpfile
        self.base_offset = 0

        self.register()

    # pylint: disable=unused-argument
    def open(self, args: str, from_tty: bool) -> None:
        argv = shlex.split(args)
        if len(argv) < 2:
            raise gdb.GdbError("kdumpfile target requires kernel image and vmcore")

        vmlinux = argv[0]
        filename = argv[1]

        try:
            self.kdump = kdumpfile(file=filename)
        except Exception as e:
            raise gdb.GdbError("Failed to open `{}': {}"
                               .format(filename, str(e)))

        # pylint: disable=unsupported-assignment-operation
        self.kdump.attr['addrxlat.ostype'] = 'linux'

        KERNELOFFSET = "linux.vmcoreinfo.lines.KERNELOFFSET"
        try:
            attr = self.kdump.attr.get(KERNELOFFSET, "0") # pylint: disable=no-member
            self.base_offset = int(attr, base=16)
        except (TypeError, ValueError):
            pass

        # Load the kernel at the relocated address
        # Unfortunately, the percpu section has an offset of 0 and
        # ends up getting placed at the offset base.  This is easy
        # enough to handle in the percpu code.
        result = gdb.execute("symbol-file {} -o {:#x}"
                             .format(vmlinux, self.base_offset),
                             to_string=True)

        if self.debug:
            print(result)

        # We don't have an exec-file so we need to set the architecture
        # explicitly.
        arch = gdb.objfiles()[0].architecture.name()
        result = gdb.execute("set architecture {}".format(arch), to_string=True)
        if self.debug:
            print(result)


    def close(self) -> None:
        try:
            self.unregister()
        except RuntimeError:
            pass
        del self.kdump

    @classmethod
    def report_error(cls, addr: int, length: int, error: Exception) -> None:
        print("Error while reading {:d} bytes from {:#x}: {}"
              .format(length, addr, str(error)),
              file=sys.stderr)

    # pylint: disable=unused-argument
    def xfer_partial(self, obj: int, annex: str, readbuf: bytearray,
                     writebuf: bytearray, offset: int, ln: int) -> int:
        ret = -1
        if obj == self.TARGET_OBJECT_MEMORY:
            try:
                r = self.kdump.read(KDUMP_KVADDR, offset, ln)
                readbuf[:] = r
                ret = ln
            except EOFException as e:
                if self.debug:
                    self.report_error(offset, ln, e)
                raise gdb.TargetXferEOF(str(e))
            # pylint: disable=no-member
            except (NoDataException, addrxlat.exceptions.NoDataError) as e:
                if self.debug:
                    self.report_error(offset, ln, e)
                raise gdb.TargetXferUnavailable(str(e))
            except AddressTranslationException as e:
                if self.debug:
                    self.report_error(offset, ln, e)
                raise gdb.TargetXferUnavailable(str(e))
        else:
            raise IOError("Unknown obj type")
        return ret

    # pylint: disable=unused-argument
    def thread_alive(self, ptid: PTID) -> bool:
        return True

    def pid_to_str(self, ptid: PTID) -> str:
        return "pid {:d}".format(ptid[1])

    def set_fetch_registers(self, callback: TargetFetchRegisters) -> None:
        self._fetch_registers = callback # type: ignore

    def fetch_registers(self, thread: gdb.InferiorThread,
                        register: gdb.Register) -> None:
        try:
            return self._fetch_registers(thread, register) # type: ignore
        except AttributeError:
            raise NotImplementedError("Target did not define fetch_registers callback")

    def prepare_to_store(self, thread: gdb.InferiorThread) -> None:
        pass

    # We don't need to store anything; The regcache is already written.
    # pylint: disable=unused-argument
    def store_registers(self, thread: gdb.InferiorThread,
                        register: gdb.Register) -> None:
        pass

    # pylint: disable=unused-argument
    def has_execution(self, ptid: PTID) -> bool:
        return False
