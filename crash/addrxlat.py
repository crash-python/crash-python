# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import addrxlat
from crash.cache.syscache import utsname
from crash.util import offsetof

class TranslationContext(addrxlat.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read_caps = addrxlat.CAPS(addrxlat.KVADDR)
        self.uint32_ptr = gdb.lookup_type('uint32_t').pointer()
        self.uint64_ptr = gdb.lookup_type('uint64_t').pointer()

    def cb_sym(self, symtype, *args):
        if symtype == addrxlat.SYM_VALUE:
            ms = gdb.lookup_minimal_symbol(args[0])
            if ms is not None:
                return int(ms.value().address)
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

        return super().cb_sym(symtype, *args)

    def cb_read32(self, faddr):
        return int(gdb.Value(faddr.addr).cast(self.uint32_ptr).dereference())

    def cb_read64(self, faddr):
        return int(gdb.Value(faddr.addr).cast(self.uint64_ptr).dereference())

class CrashAddressTranslation(object):
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

        self.is_non_auto = False
        map = self.system.get_map(addrxlat.SYS_MAP_MACHPHYS_KPHYS)
        for range in map:
            if range.meth == addrxlat.SYS_METH_NONE:
                continue
            meth = self.system.get_meth(range.meth)
            if meth.kind != addrxlat.LINEAR or meth.off != 0:
                self.is_non_auto = True
                break

__impl = CrashAddressTranslation()
def addrxlat_context():
    return __impl.context

def addrxlat_system():
    return __impl.system

def addrxlat_is_non_auto():
    return __impl.is_non_auto
