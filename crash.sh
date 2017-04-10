#!/bin/bash
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

usage() {
cat <<END >&2
usage: $(basename $0) [-d|--search-dir <debuginfo/module dir>] <vmlinux> <vmcore>
END
exit 1
}

TEMP=$(getopt -o 'd:' --long 'search-dir:' -n "$(basename $0)" -- "$@")

if [ $? -ne 0 ]; then
    echo "Terminating." >&2
    exit 1
fi

eval set -- "$TEMP"
unset TEMP

while true; do
    case "$1" in
        '-d'|'--search-dir')
            SEARCHDIRS="$SEARCHDIRS $2"
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

_cleanup() {
    rm -rf "$TMPDIR"
}

TMPDIR=$(mktemp -d /tmp/crash.XXXXXX)
trap _cleanup EXIT

GDBINIT="$TMPDIR/gdbinit"

# If we're using crash.sh from the git repo, use the modules from the git repo
DIR="$(dirname $0)"
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
cat << EOF >> $GDBINIT
set build-id-verbose 0
set python print-stack full
set prompt py-crash> 
set height 0
set print pretty on

python
import crash
path = "$SEARCHDIRS".split(' ')
try:
   x = crash.Session("$KERNEL", "$VMCORE", "$ZKERNEL", path)
except gdb.error as e:
    print(str(e))
except RuntimeError as e:
    print("Failed to open {}: {}".format("$VMCORE", str(e)))
EOF

gdb -nh -q -x $GDBINIT
