#!/bin/bash

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
    $RUN/run-gdb.sh -x $TOPDIR/kernel-tests/unittest-prepare.py \
		    -x $TOPDIR/kernel-tests/unittest-bootstrap.py
done
