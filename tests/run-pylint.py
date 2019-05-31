# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from pylint import lint
import os
import shlex

argv = shlex.split(os.environ['PYLINT_ARGV'])

sys.exit(lint.Run(argv))
