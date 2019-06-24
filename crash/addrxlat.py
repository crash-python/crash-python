# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import addrxlat
from crash.cache.syscache import utsname
from crash.util import offsetof
from crash.util.symbols import Types

import gdb

types = Types(['uint32_t *', 'uint64_t *'])

class TranslationContext(addrxlat.Context):
    def __init__(self, *args: int, **kwargs: int) -> None:
        super().__init__(*args, **kwargs)
        self.read_caps = addrxlat.CAPS(addrxlat.KVADDR)

    def cb_sym(self, symtype: int, *args: str) -> int:
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
                ret = offsetof(sym.type, args[1], True)
                if ret is None:
                    raise RuntimeError("offsetof can't return None with errors=True")

        return super().cb_sym(symtype, *args)

    def cb_read32(self, faddr: addrxlat.FullAddress) -> int:
        v = gdb.Value(faddr.addr).cast(types.uint32_t_p_type)
        return int(v.dereference())

    def cb_read64(self, faddr: addrxlat.FullAddress) -> int:
        v = gdb.Value(faddr.addr).cast(types.uint64_t_p_type)
        return int(v.dereference())

class CrashAddressTranslation:
    def __init__(self) -> None:
        try:
            target = gdb.current_target()
            self.context = target.kdump.get_addrxlat_ctx()
            self.system = target.kdump.get_addrxlat_sys()
        except AttributeError:
            self.context = TranslationContext()
            self.system = addrxlat.System()
            self.system.os_init(self.context,
                                arch=utsname.machine,
                                type=addrxlat.OS_LINUX)

        self.is_non_auto = False
        xlatmap = self.system.get_map(addrxlat.SYS_MAP_MACHPHYS_KPHYS)
        for addr_range in xlatmap:
            if addr_range.meth == addrxlat.SYS_METH_NONE:
                continue
            meth = self.system.get_meth(addr_range.meth)
            if meth.kind != addrxlat.LINEAR or meth.off != 0:
                self.is_non_auto = True
                break
