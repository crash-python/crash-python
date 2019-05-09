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
STEXT_KALLSYMS=$(awk '$3 == "_stext" { print $1 }' /proc/kallsyms)
STEXT_VMLINUX=$(nm "$VMLINUX" | awk '$3 == "_stext" { print $1 }')

#
# Due to the KASLR done by the kernel, the symbol addresses contained in
# the "vmlinux" file are not exactly what's used by the running system.
# To translate the addresses in the "vmlinux" file, to the addresses
# being used on the live system, we have to offset all of the "vmlinux"
# addresses by the KASLR offset. Here we determine the KASLR offset by
# determining the difference between the address of the "_stext" symbol
# as reported by "/proc/kallsyms" and the "vminlinux" file; this offset
# is then later fed into GDB when loading the "vmlinux" symbols.
#
OFFSET=$(python -c "print(int('$STEXT_KALLSYMS', 16) - int('$STEXT_VMLINUX', 16))")

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

add-symbol-file $VMLINUX -o $OFFSET
target core /proc/kcore

#
# Since we're readying from /proc/kcore and the contents of that can
# change, we disable as much of GDB's caching as we can.
#
set stack-cache off
set code-cache off
set dcache size 1
set dcache line-size 2
set non-stop on

python
import crash.session
x = crash.session.Session(None, None, None)
end
EOF

$GDB -nh -q -x "$GDBINIT"
