# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import kdump.target

def current_target() -> kdump.target.Target:
    target = gdb.current_target()
    if target is None:
        raise ValueError("No current target")

    if not isinstance(target, kdump.target.Target):
        raise ValueError(f"Current target {type(target)} is not supported")

    return target
