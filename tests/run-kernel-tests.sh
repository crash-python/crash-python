#!/bin/bash

usage() {
cat <<END >&2
usage: $(basename $0) [options] <ini-files-to-test>

Options:
-t <test_match> | --tests <test_match>
    test_match is a pathname-style wildcard expression to specify
    which tests to run
END
}

TEMP=$(getopt -o 'ht:' --long 'help,tests:' -n "$(basename $0)" -- "$@")

if test $? -ne 0; then
	usage
	exit 1
fi

eval set -- "$TEMP"
unset TEMP

TESTS=""
while true; do
    case "$1" in
    '-t' | '--tests')
	TESTS="$2"
	shift 2
	;;
    '-h' | '--help')
	usage
	exit 0
	;;
    --)
	shift
	break
	;;
    *)
	echo "internal error [$1]" >&2
	exit 1
    esac
done

if test $# -eq 0; then
    echo "No ini files specified.  Nothing to do."
    exit 0
fi

cleanup() {
    test -n "$DIR" && rm -rf "$DIR"
}

trap cleanup EXIT

RUN="$(dirname "$0")"

DIR=$(mktemp -d "/tmp/cp-kernel-tests.XXXXXX")
export CRASH_PYTHON_TESTDIR=$DIR

TOPDIR=$(realpath "$(dirname "$0")"/..)
for f in "$@"; do
    export CRASH_PYTHON_TESTFILE="$f"
    if test -n "$TESTS"; then
	export CRASH_PYTHON_TESTS="$TESTS"
	echo "Running subset $TESTS"
    fi
    $RUN/run-gdb.sh -x $TOPDIR/kernel-tests/unittest-prepare.py \
		    -x $TOPDIR/kernel-tests/unittest-bootstrap.py
done
