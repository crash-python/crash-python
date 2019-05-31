#!/bin/bash

DIR=$(dirname "$0")
echo "Starting gdb"
exec crash-python-gdb -nx -batch -x $DIR/gdbinit-boilerplate "$@"
