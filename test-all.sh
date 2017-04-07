#!/bin/sh

make -C tests
gdb -batch -ex "source tests/unittest-bootstrap.py"
