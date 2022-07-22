#!/bin/bash

DIR=$(dirname "$0")

if test -z "$GDB"; then
	GDB=crash-python-gdb
fi

echo "Starting gdb"
exec $GDB $GDB_CMDLINE -nx -batch -x $DIR/gdbinit-boilerplate "$@"
