#!/bin/bash

DIR="/home/jeffm/src/git/github/crash-python"

if [ "$#" -ne 2 ]; then
	echo "usage: crash <vmlinux> <vmcore>" >&2
	exit 1
fi

_cleanup() {
	rm -rf "$TMPDIR"
}

TMPDIR=$(mktemp -d /tmp/crash.XXXXXX)
trap _cleanup EXIT

GDBINIT="$TMPDIR/gdbinit"


if [ -e "$DIR/setup.py" ]; then
echo "python sys.path.insert(0, '$DIR')" >> $GDBINIT
fi

ZKERNEL="$1"
KERNEL="${ZKERNEL%.gz}"
if test "$KERNEL" != "$ZKERNEL"; then
	KERNEL="$TMPDIR/$(basename "$KERNEL")"
	zcat $ZKERNEL > $KERNEL
else
	KERNEL="$ZKERNEL"
fi

cat << EOF >> $GDBINIT
set python print-stack full
set prompt py-crash> 
set height 0
file $KERNEL
python import crash
python x = crash.Session("$2")
EOF

VMCORE=$2
if [ ! -e "$KERNEL" ]; then
	echo "Kernel file \"$KERNEL\" doesn't exist." >&2
	exit 1
elif [ ! -e "$VMCORE" ]; then
	echo "Core file \"$VMCORE\" doesn't exist." >&2
	exit 1
fi

gdb -q -x $GDBINIT
