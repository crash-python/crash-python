#!/bin/sh

rm -rf build/lib/crash
python3 setup.py build
make -C tests
crash-python-gdb -batch -ex "source tests/unittest-bootstrap.py"
