#!/bin/bash

if ! python3 -c 'import pylint' 2> /dev/null; then
    echo "pylint is not installed"
    exit 0
fi

export PYLINT_ARGV="$@"

DIR=$(dirname "$0")
exec $DIR/run-gdb.sh -x $DIR/run-pylint.py
