# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

# gdb sets sys.executable as python regardless of whether it's python2 or 3
import sys
sys.executable = "/usr/bin/python3"

from pylint import lint
import os
import shlex

argv = shlex.split(os.environ['PYLINT_ARGV'])

sys.exit(lint.Run(argv))
