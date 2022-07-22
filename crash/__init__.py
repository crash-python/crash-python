# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

def archname() -> str:
    return gdb.selected_inferior().architecture().name()
