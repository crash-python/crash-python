#!/usr/bin/env python
# -*- coding: utf-8 -*-,
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath("."))

test_loader = unittest.TestLoader()
test_suite = test_loader.discover('tests', pattern='test_*.py')
unittest.TextTestRunner(verbosity=2).run(test_suite)
