# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import drgn
import sys


class Target(gdb.Target):
    def __init__(self, vmlinux, debug=False):
        super(Target, self).__init__()
        self.debug = debug
        self.shortname = "drgn"
        self.longname = "Use Linux's /proc/kcore as a target through drgn"
        self.vmlinux = vmlinux
        self.register()

    def open(self, filename, from_tty):
        if filename != "/proc/kcore":
            raise gdb.GdbError("incorrect file target - should be /proc/kcore")

        self.drgn = drgn.Program()
        self.drgn.set_kernel()

        try:
            self.drgn.load_default_debug_info()
        except drgn.MissingDebugInfoError as e:
            print(str(e), file=sys.stderr)

        vmcoreinfo = dict(
            [
                line.split("=")
                for line in self.drgn["vmcoreinfo_data"].string_().decode().splitlines()
            ]
        )
        offset = int(vmcoreinfo["KERNELOFFSET"], base=16)
        gdb.execute("add-symbol-file {} -o {:#x}".format(self.vmlinux, offset))
        gdb.execute("file {}".format(self.vmlinux))

    def close(self):
        try:
            self.unregister()
        except:
            pass
        del self.drgn

    @classmethod
    def report_error(cls, addr, length, error):
        print(
            "Error while reading {:d} bytes from {:#x}: {}".format(
                length, addr, str(error)
            ),
            file=sys.stderr,
        )

    def xfer_partial(self, obj, annex, readbuf, writebuf, offset, ln):
        ret = -1
        if obj == self.TARGET_OBJECT_MEMORY:
            try:
                r = self.drgn.read(offset, ln)
                readbuf[:] = r
                ret = len(r)
            except drgn.FaultError as e:
                if self.debug:
                    self.report_error(offset, ln, e)
                raise gdb.TargetXferUnavailable(str(e))
        else:
            raise IOError("Unknown obj type")
        return ret

    def thread_alive(self, ptid):
        return True

    def pid_to_str(self, ptid):
        return "pid {:d}".format(ptid[1])

    def fetch_registers(self, register):
        return False

    def prepare_to_store(self, thread):
        pass

    # We don't need to store anything; The regcache is already written.
    def store_registers(self, thread):
        pass

    def has_execution(self, ptid):
        return False
