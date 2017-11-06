# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys

if sys.version_info.major >= 3:
    long = int

import addrxlat
from crash.infra import CrashBaseClass, export
from crash.cache.syscache import utsname
from crash.util import offsetof

class TranslationContext(addrxlat.Context):
    def __init__(self, *args, **kwargs):
        super(TranslationContext, self).__init__(*args, **kwargs)
        self.read_caps = addrxlat.CAPS(addrxlat.KVADDR)
        self.uint32_ptr = gdb.lookup_type('uint32_t').pointer()
        self.uint64_ptr = gdb.lookup_type('uint64_t').pointer()

    def cb_sym(self, symtype, *args):
        if symtype == addrxlat.SYM_VALUE:
            ms = gdb.lookup_minimal_symbol(args[0])
            if ms is not None:
                return long(ms.value().address)
        elif symtype == addrxlat.SYM_SIZEOF:
            sym = gdb.lookup_symbol(args[0], None)[0]
            if sym is not None:
                return sym.type.sizeof
        elif symtype == addrxlat.SYM_OFFSETOF:
            sym = gdb.lookup_symbol(args[0], None, gdb.SYMBOL_STRUCT_DOMAIN)[0]
            if sym is None:
                # this works for typedefs:
                sym = gdb.lookup_symbol(args[0], None)[0]
            if sym is not None:
                return offsetof(sym.type, args[1])

        return super(TranslationContext, self).cb_sym(symtype, *args)

    def cb_read32(self, faddr):
        return long(gdb.Value(faddr.addr).cast(self.uint32_ptr).dereference())

    def cb_read64(self, faddr):
        return long(gdb.Value(faddr.addr).cast(self.uint64_ptr).dereference())

class CrashAddressTranslation(CrashBaseClass):
    def __init__(self):
        try:
            target = gdb.current_target()
            self.context = target.kdump.get_addrxlat_ctx()
            self.system = target.kdump.get_addrxlat_sys()
        except AttributeError:
            self.context = TranslationContext()
            self.system = addrxlat.System()
            self.system.os_init(self.context,
                                arch = utsname.machine,
                                type = addrxlat.OS_LINUX)

    @export
    def addrxlat_context(self):
        return self.context

    @export
    def addrxlat_system(self):
        return self.system
