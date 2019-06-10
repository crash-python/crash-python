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

python
try:
    gdb.execute('set print thread-events 0')
    target.setup_task()
    gdb.execute("thread 1", to_string=True)
    sys.exit(0)
except gdb.error as e:
    print(e)
    print("This version of gdb is not compatible with crash-python")
    sys.exit(1)
end
