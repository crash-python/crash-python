# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.exceptions import DelayedAttributeError

class LogTypeException(Exception):
    pass

class LogInvalidOption(Exception):
    pass
