#!/bin/bash

if [[ "$EUID" -ne "0" ]]; then
	echo "ERROR: Must be run as root." >&2
	exit 1
fi

for gdb in crash-python-gdb gdb; do
	if $gdb -v >/dev/null 2>/dev/null; then
		GDB=$gdb
		break
	fi
done

if [[ -z "$GDB" ]]; then
	echo "ERROR: gdb is not available." >&2
	exit 1
fi

GDBINIT=$(mktemp)
trap "rm '$GDBINIT'" EXIT

VMLINUX="/usr/lib/debug/boot/vmlinux-$(uname -r)"

DIR="$(dirname $0)"
if [[ -e "$DIR/setup.py" ]]; then
	pushd $DIR >/dev/null
	rm -rf build/lib/crash
	python3 setup.py build >/dev/null
	echo "python sys.path.insert(0, '$DIR/build/lib')" >>"$GDBINIT"
	popd >/dev/null
fi

cat <<EOF >>"$GDBINIT"
set python print-stack full
set height 0
set print pretty on

python
from kcore.target import Target
target = Target("$VMLINUX", debug=False)
end

target drgn /proc/kcore

python
import crash.session
x = crash.session.Session(None, None, None)
target.unregister()
del target
end
EOF

$GDB -nh -q -x "$GDBINIT"
