#!/bin/sh

rm -rf build/lib/crash
python3 setup.py -q build
make -C tests -s
crash-python-gdb -nx -batch -ex "source tests/unittest-bootstrap.py"
