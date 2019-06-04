#!/bin/bash

set -e

DIR=$(realpath $(dirname $0)/..)

cat << END
# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest

class TestImports(unittest.TestCase):
END

for f in $(cd $DIR ; find crash kdump -name '*.py'); do
	path=$(echo $f | sed -e 's#/__init__.py##' -e 's#.py##')
	name=$(echo $path | tr / .)
	tname=$(echo $path | tr / _)

cat <<END
    def test_$tname(self):
        """Test importing $name"""
        import $name

END
done
