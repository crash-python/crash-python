# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import sys
from kdumpfile import kdumpfile, KDUMP_KVADDR
from kdumpfile.exceptions import *
import addrxlat
import crash.arch
import crash.arch.x86_64

class SymbolCallback(object):
    "addrxlat symbolic callback"

    def __init__(self, ctx=None, *args, **kwargs):
        super(SymbolCallback, self).__init__(*args, **kwargs)
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
    def __init__(self, vmcore, debug=False):
        if not isinstance(vmcore, kdumpfile):
            raise TypeError("vmcore must be of type kdumpfile")
        self.arch = None
        self.debug = debug
        self.kdump = vmcore
        ctx = self.kdump.get_addrxlat_ctx()
        ctx.cb_sym = SymbolCallback(ctx)
        self.kdump.attr['addrxlat.ostype'] = 'linux'

        # So far we've read from the kernel image, now that we've setup
        # the architecture, we're ready to plumb into the target
        # infrastructure.
        super(Target, self).__init__()

    def setup_arch(self):
        archname = self.kdump.attr.arch.name
        archclass = crash.arch.get_architecture(archname)
        if not archclass:
            raise NotImplementedError("Architecture {} is not supported yet."
                                      .format(archname))

        # Doesn't matter what symbol as long as it's everywhere
        # Use vsnprintf since 'printk' can be dropped with CONFIG_PRINTK=n
        sym = gdb.lookup_symbol('vsnprintf', None)[0]
        if sym is None:
            raise RuntimeError("Missing vsnprintf indicates there is no kernel image loaded.")
        if sym.symtab.objfile.architecture.name() != archclass.ident:
            raise TypeError("Dump file is for `{}' but provided kernel is for `{}'"
                            .format(archname, archclass.ident))

        self.arch = archclass()

    @classmethod
    def report_error(cls, addr, length, error):
        print("Error while reading {:d} bytes from {:#x}: {}"
              .format(length, addr, str(error)),
              file=sys.stderr)

    def to_xfer_partial(self, obj, annex, readbuf, writebuf, offset, ln):
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

    @staticmethod
    def to_thread_alive(ptid):
        return True

    @staticmethod
    def to_pid_to_str(ptid):
        return "pid {:d}".format(ptid[1])

    def to_fetch_registers(self, register):
        thread = gdb.selected_thread()
        self.arch.fetch_register(thread, register.regnum)
        return True

    @staticmethod
    def to_prepare_to_store(thread):
        pass

    # We don't need to store anything; The regcache is already written.
    @staticmethod
    def to_store_registers(thread):
        pass

    @staticmethod
    def to_has_execution(ptid):
        return False
