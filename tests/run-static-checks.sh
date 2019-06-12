#!/bin/bash

# mypy spawns multiple subprocesses that invoke the interpreter
# separately.  As a result, we fail to import the gdb and kdumpfile
# modules and fail.

if ! python3 -c 'import mypy' 2> /dev/null; then
    echo "mypy is not installed"
    exit 0
fi

set -e

DIR=$(dirname "$0")
export MYPYPATH="$(realpath $DIR/stubs)"

python3 $DIR/run-mypy.py
