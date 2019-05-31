# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import unittest
import sys
import os
import os.path
import configparser
import gzip
import shutil

config = configparser.ConfigParser()
filename = os.environ['CRASH_PYTHON_TESTFILE']
try:
    f = open(filename)
    config.read_file(f)
except FileNotFoundError as e:
    print(f"{str(e)}")
    sys.exit(1)

try:
    vmcore = config['test']['vmcore']
except KeyError:
    print(f"{filename} doesn't contain the required sections.")
    sys.exit(1)

roots = config['test'].get('root', None)
vmlinux_debuginfo = config['test'].get('vmlinux_debuginfo', None)
module_path = config['test'].get('module_path', None)
module_debuginfo_path = config['test'].get('module_debuginfo_path', None)

from crash.kernel import CrashKernel
kernel = CrashKernel(roots=roots, vmlinux_debuginfo=vmlinux_debuginfo,
                     module_path=module_path,
                     module_debuginfo_path=module_debuginfo_path)

kernel.setup_tasks()
kernel.load_modules()

test_loader = unittest.TestLoader()
test_suite = test_loader.discover('kernel-tests', pattern='test_*.py')
ret = unittest.TextTestRunner(verbosity=2).run(test_suite)
if not ret.wasSuccessful():
    sys.exit(1)
sys.exit(0)
