# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

# Perform some sanity checks to ensure that we can actually work
import gdb
import kdumpfile

from crash.exceptions import IncompatibleGDBError, IncompatibleKdumpfileError

try:
    x1 = gdb.Target
    del x1
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Target") from e

try:
    x2 = gdb.lookup_symbol('x', None)
    del x2
except TypeError as e:
    raise IncompatibleGDBError("a compatible gdb.lookup_symbol") from e

try:
    x3 = gdb.MinSymbol
    del x3
except AttributeError as e:
    raise IncompatibleGDBError("gdb.MinSymbol") from e

try:
    x4 = gdb.RegisterDescriptor
    del x4
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Register") from e

try:
    x5 = gdb.LinuxKernelTarget
    del x5
except AttributeError as e:
    raise IncompatibleGDBError("gdb.LinuxKernelTarget") from e

if not hasattr(kdumpfile.kdumpfile, "from_pointer"):
    raise IncompatibleKdumpfileError("from_pointer method")
