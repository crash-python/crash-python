#!/bin/bash
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

DIR="/home/jeffm/src/git/github/crash-python"

usage() {
cat <<END >&2
usage: $(basename $0) [-d|--debug-dir <debuginfo dir>] <vmlinux> <vmcore>
END
exit 1
}

TEMP=$(getopt -o 'd:' --long '--debug-dir:' -n "$(basename $0)" -- "$@")

if [ $? -ne 0 ]; then
    echo "Terminating." >&2
    exit 1
fi

eval set -- "$TEMP"
unset TEMP

while true; do
    case "$1" in
        '-d'|'--debug-dir')
            DEBUGINFO="$2"
            shift 2
            continue
        ;;
        '--')
            shift
            break
        ;;
        *)
            echo "internal error [$1]" >&2
            exit 1
        ;;
    esac
done

if [ "$#" -ne 2 ]; then
    usage
fi

if [ -n "$DEBUGINFO" ]; then
    DEBUGINFO="set debug-file-directory $DEBUGINFO"
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

VMCORE=$2
if [ ! -e "$KERNEL" ]; then
    echo "Kernel file \"$KERNEL\" doesn't exist." >&2
    exit 1
elif [ ! -e "$VMCORE" ]; then
    echo "Core file \"$VMCORE\" doesn't exist." >&2
    exit 1
fi

cat << EOF >> $GDBINIT
set python print-stack full
set prompt py-crash> 
set height 0
$DEBUGINFO
file $KERNEL
python import crash
python x = crash.Session("$VMCORE")
EOF

gdb -nh -q -x $GDBINIT
