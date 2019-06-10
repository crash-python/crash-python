# This gdbinit segment tests the invoked gdb for compatibility as
# a crash-python host.
python
import sys
import os

from crash.exceptions import IncompatibleGDBError

try:
    import crash.requirements
except IncompatibleGDBError as e:
    print(e)
    sys.exit(1)
end
