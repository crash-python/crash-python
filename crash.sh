#!/bin/bash
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

usage() {
cat <<END >&2
usage: $(basename $0) [options] <vmlinux> <vmcore>

Options:
-r <dir> | --root <dir>
    Use the specified directory as the root for all file searches.  When
    using properly configured .build-id symbolic links, this is the
    best method to use as the debuginfo will be loaded automatically via
    gdb without searching for filenames.

-m <dir> | --modules <dir>
    Use the specified directory to search for modules

-d <dir> | --modules-debuginfo <dir>
    Use the specified directory to search for module debuginfo

-D <dir> | --vmlinux-debuginfo <dir>
    Use the specified directory to search for vmlinux debuginfo

-b <dir> | --build-dir <dir>
    Use the specified directory as the root for all file searches.  This
    directory should be the root of a built kernel source tree.  This is
    shorthand for "-r <dir> -m . -d . -D ." and will override preceding
    options.

Debugging options:
--debug
    Enable noisy output for debugging the debugger
-v | --verbose
    Enable verbose output for debugging the debugger
--gdb
    Run the embedded gdb underneath a separate gdb instance.  This is useful
    for debugging issues in gdb that are seen while running crash-python.
--valgrind
    Run the embedded gdb underneath valgrind.  This is useful
    for debugging memory leaks in gdb patches.
END
exit 1
}

TEMP=$(getopt -o 'vr:d:m:D:b:h' --long 'verbose,root:,modules-debuginfo:,modules:,vmlinux-debuginfo:,build-dir:,debug,gdb,valgrind,help' -n "$(basename $0)" -- "$@")

if [ $? -ne 0 ]; then
    usage
fi

eval set -- "$TEMP"
unset TEMP

VERBOSE=False
DEBUG=False

while true; do
    case "$1" in
        '-r'|'--root')
            if test -z "$SEARCH_DIRS"; then
                SEARCH_DIRS="$2"
            else
                SEARCH_DIRS="$SEARCH_DIRS $2"
            fi
            shift 2
            continue
        ;;
        '-m'|'--modules')
            if test -z "$MODULES"; then
                MODULES="$2"
            else
                MODULES="$MODULES $2"
            fi
            shift 2
            continue
        ;;
        '-d'|'--modules-debuginfo')
            if test -z "$MODULES_DEBUGINFO"; then
                MODULES_DEBUGINFO="$2"
            else
                MODULES_DEBUGINFO="$MODULES_DEBUGINFO $2"
            fi
            shift 2
            continue
        ;;
        '-D'|'--vmlinux-debuginfo')
            if test -z "$VMLINUX_DEBUGINFO"; then
                VMLINUX_DEBUGINFO="$2"
            else
                VMLINUX_DEBUGINFO="$VMLINUX_DEBUGINFO $2"
            fi
            shift 2
            continue
        ;;
        '-b'|'--build-dir')
            SEARCH_DIRS="$2"
            VMLINUX_DEBUGINFO="."
            MODULES="."
            MODULES_DEBUGINFO="."
            shift 2
            continue
            ;;
        '-v'|'--verbose')
            VERBOSE="True"
            shift
            continue
        ;;
        '--debug')
            DEBUG="True"
            shift
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
        '-h'|'--help')
            usage ;;
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

set -e

GDB=
for gdb in crash-python-gdb gdb; do
    if $gdb -v > /dev/null 2> /dev/null; then
        GDB=$gdb
        break
    fi
done

if [ -z "$GDB" ]; then
    echo "ERROR: gdb is not available." >&2
    exit 1
fi

# If we're using crash.sh from the git repo, use the modules from the git repo
DIR="$(dirname $0)"
if [ -e "$DIR/setup.py" ]; then
    pushd $DIR > /dev/null
    rm -rf build/lib/crash
    python3 setup.py build > /dev/null
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
for path in $SEARCH_DIRS; do
    if test -n "$DFD"; then
        DFD="$DFD:$path"
    else
        DFD="$path"
    fi
done
cat << EOF >> $GDBINIT
set debug-file-directory $DFD:/usr/lib/debug
set build-id-verbose 0
set python print-stack full
set prompt py-crash> 
set height 0
set print pretty on

file "$KERNEL"

python
from kdump.target import Target
target = Target(debug=False)
end

target kdumpfile $VMCORE

python
import sys
import traceback
try:
    import crash.session
    from crash.kernel import CrashKernel
except RuntimeError as e:
    print("crash-python: {}, exiting".format(str(e)), file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

roots = None
module_path = None
module_debuginfo_path = None
vmlinux_debuginfo = None
verbose=$VERBOSE
debug=$DEBUG

s = "$SEARCH_DIRS"
if len(s) > 0:
    roots = s.split(" ")

s = "$VMLINUX_DEBUGINFO"
if len(s) > 0:
    vmlinux_debuginfo = s.split(" ")

s = "$MODULES"
if len(s) > 0:
    module_path = s.split(" ")

s = "$MODULES_DEBUGINFO"
if len(s) > 0:
    module_debuginfo_path = s.split(" ")

try:
    kernel = CrashKernel(roots, vmlinux_debuginfo, module_path,
                         module_debuginfo_path, verbose, debug)

    x = crash.session.Session(kernel, verbose=verbose, debug=debug)
    print("The 'pyhelp' command will list the command extensions.")
except gdb.error as e:
    print("crash-python: {}, exiting".format(str(e)), file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
except RuntimeError as e:
    print("crash-python: Failed to open {}.  {}".format("$VMCORE", str(e)),
          file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

target.unregister()
del target
EOF

# This is how we debug gdb problems when running crash
if [ "$DEBUGMODE" = "gdb" ]; then
    RUN="run -nx -q -x $GDBINIT"

    echo $RUN > $TMPDIR/gdbinit-debug
    gdb $GDB -nx -q -x $TMPDIR/gdbinit-debug
elif [ "$DEBUGMODE" = "valgrind" ]; then
    valgrind --keep-stacktraces=alloc-and-free $GDB -nh -q -x $GDBINIT
else
    $GDB -nx -q -x $GDBINIT
fi
