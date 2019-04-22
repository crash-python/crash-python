# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import sys
from kdumpfile import kdumpfile, KDUMP_KVADDR
from kdumpfile.exceptions import *
import addrxlat

class SymbolCallback(object):
    "addrxlat symbolic callback"

    def __init__(self, ctx=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx

    def __call__(self, symtype, *args):
        if self.ctx is not None:
            try:
                return self.ctx.next_cb_sym(symtype, *args)
            except addrxlat.BaseException:
                self.ctx.clear_err()

        if symtype == addrxlat.SYM_VALUE:
            ms = gdb.lookup_minimal_symbol(args[0])
            if ms is not None:
                return int(ms.value().address)
        raise addrxlat.NoDataError()

class Target(gdb.Target):
    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug
        self.shortname = "kdumpfile"
        self.longname = "Use a Linux kernel kdump file as a target"

        self.register()

    def open(self, filename, from_tty):

        if len(gdb.objfiles()) == 0:
            raise gdb.GdbError("kdumpfile target requires kernel to be already loaded for symbol resolution")
        try:
            self.kdump = kdumpfile(file=filename)
        except Exception as e:
            raise gdb.GdbError("Failed to open `{}': {}"
                                .format(filename, str(e)))

        self.kdump.attr['addrxlat.ostype'] = 'linux'
        ctx = self.kdump.get_addrxlat_ctx()
        ctx.cb_sym = SymbolCallback(ctx)

        KERNELOFFSET = "linux.vmcoreinfo.lines.KERNELOFFSET"
        try:
            attr = self.kdump.attr.get(KERNELOFFSET, "0")
            self.base_offset = int(attr, base=16)
        except Exception as e:
            self.base_offset = 0

        vmlinux = gdb.objfiles()[0].filename

        # Load the kernel at the relocated address
        gdb.execute("add-symbol-file {} -o {:#x} -s .data..percpu 0"
                    .format(vmlinux, self.base_offset))

        # Clear out the old symbol cache
        gdb.execute("file {}".format(vmlinux))

    def close(self):
        try:
            self.unregister()
        except:
            pass
        del self.kdump

    @classmethod
    def report_error(cls, addr, length, error):
        print("Error while reading {:d} bytes from {:#x}: {}"
              .format(length, addr, str(error)),
              file=sys.stderr)

    def xfer_partial(self, obj, annex, readbuf, writebuf, offset, ln):
        ret = -1
        if obj == self.TARGET_OBJECT_MEMORY:
            try:
                r = self.kdump.read(KDUMP_KVADDR, offset, ln)
                readbuf[:] = r
                ret = ln
            except EOFException as e:
                if self.debug:
                    self.report_error(offset, ln, e)
                raise gdb.TargetXferEof(str(e))
            except NoDataException as e:
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
