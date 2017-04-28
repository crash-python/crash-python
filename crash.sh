#!/bin/bash
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

usage() {
cat <<END >&2
usage: $(basename $0) [-d|--search-dir <debuginfo/module dir>] <vmlinux> <vmcore>
END
exit 1
}

TEMP=$(getopt -o 'd:' --long 'search-dir:,gdb,valgrind,nofiles' -n "$(basename $0)" -- "$@")

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
        '--gdb')
            DEBUGMODE=gdb
            shift
            continue
            ;;
        '--valgrind')
            DEBUGMODE=valgrind
            shift
            continue
            ;;
        '--nofiles')
            NOFILES=yes
            shift
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

if [ "$#" -ne 2 -a -z "$NOFILES" ]; then
    usage
fi

_cleanup() {
    rm -rf "$TMPDIR"
}

TMPDIR=$(mktemp -d /tmp/crash.XXXXXX)
trap _cleanup EXIT

GDBINIT="$TMPDIR/gdbinit"

set -e

# If we're using crash.sh from the git repo, use the modules from the git repo
DIR="$(dirname $0)"
if [ -e "$DIR/setup.py" ]; then
    pushd $DIR > /dev/null
    rm -rf build/lib/crash
    python setup.py build > /dev/null
    echo "python sys.path.insert(0, '$DIR/build/lib')" >> $GDBINIT
    popd > /dev/null
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
import crash.session
path = "$SEARCHDIRS".split(' ')
try:
   x = crash.session.Session("$KERNEL", "$VMCORE", "$ZKERNEL", path)
except gdb.error as e:
    print(str(e))
except RuntimeError as e:
    print("Failed to open {}: {}".format("$VMCORE", str(e)))
EOF

# This is how we debug gdb problems when running crash
if [ "$DEBUGMODE" = "gdb" ]; then
    RUN="run -nh -q -x $GDBINIT"

    echo $RUN > /tmp/gdbinit
    gdb gdb -nh -q -x /tmp/gdbinit
elif [ "$DEBUGMODE" = "valgrind" ]; then
    valgrind --keep-stacktraces=alloc-and-free gdb -nh -q -x $GDBINIT
else
    gdb -nh -q -x $GDBINIT
fi
