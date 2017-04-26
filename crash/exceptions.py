# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

class MissingSymbolError(RuntimeError):
    pass

class MissingTypeError(RuntimeError):
    pass

class CorruptedError(RuntimeError):
    pass

class DelayedAttributeError(AttributeError):
    def __init__(self, owner, name):
        msg = "{} has delayed attribute {} but it has not been completed."
        super(DelayedAttributeError, self).__init__(msg.format(owner, name))
