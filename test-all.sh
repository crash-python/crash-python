#!/bin/sh

rm -rf build/lib/crash
python setup.py build
make -C tests
gdb -batch -ex "source tests/unittest-bootstrap.py"
