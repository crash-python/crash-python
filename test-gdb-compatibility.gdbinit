# This gdbinit segment tests the invoked gdb for compatibility as
# a crash-python host.
python
import sys
import os

from crash.exceptions import IncompatibleGDBError

try:
    import crash.requirements
    from crash.requirements.test_target import TestTarget
    target = TestTarget()
except IncompatibleGDBError as e:
    print(e)
    sys.exit(1)
end

target testtarget foo
