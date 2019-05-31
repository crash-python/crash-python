#/bin/bash

DIR="$(dirname "$0")"
exec $DIR/run-gdb.sh -x $DIR/unittest-bootstrap.py
