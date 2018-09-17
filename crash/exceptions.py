# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

class MissingSymbolError(RuntimeError):
    """The requested symbol cannot be located."""
    pass

class MissingTypeError(RuntimeError):
    """The requested type cannot be located."""
    pass

class CorruptedError(RuntimeError):
    """A corrupted data structure has been encountered."""
    pass

class DelayedAttributeError(AttributeError):
    """
    The attribute has been declared but the symbol to fill it has not yet been
    located.
    """
    def __init__(self, owner, name):
        msg = "{} has delayed attribute {} but it has not been completed."
        super(DelayedAttributeError, self).__init__(msg.format(owner, name))
