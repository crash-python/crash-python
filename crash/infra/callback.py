# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gdb
import traceback
import sys

class CallbackCompleted(RuntimeError):
    """The callback has already been completed and is no longer valid"""
    def __init__(self, callback_obj):
        msg = "{} has already completed.".format(callback_obj.name)
        super(CallbackCompleted, self).__init__(msg)
        self.callback_obj = callback_obj

class ObjfileEventCallback(object):
    """
    A generic objfile callback class

    When GDB loads an objfile, it can perform callbacks.  These callbacks
    are triggered for every objfile loaded.  Once marked complete, the
    callback is removed so it doesn't trigger for future objfile loads.

    Derived classes need only implement the complete and check_ready
    methods.
    """
    def __init__(self):
        self.completed = True
        completed = False

        self.setup_symbol_cache_flush_callback()

        # We don't want to do lookups immediately if we don't have
        # an objfile.  It'll fail for any custom types but it can
        # also return builtin types that are eventually changed.
        if len(gdb.objfiles()) > 0:
            result = self.check_ready()
            if not (result is None or result is False):
                completed = self.callback(result)

        if completed is False:
            self.completed = False
            gdb.events.new_objfile.connect(self._new_objfile_callback)

    def complete(self):
        if not self.completed:
            gdb.events.new_objfile.disconnect(self._new_objfile_callback)
            self.completed = True
        else:
            raise CallbackCompleted(self)

    symbol_cache_flush_setup = False
    @classmethod
    def setup_symbol_cache_flush_callback(cls):
        if not cls.symbol_cache_flush_setup:
            gdb.events.new_objfile.connect(cls.flush_symbol_cache_callback)
            cls.symbol_cache_flush_setup = True


    # GDB does this itself, but Python is initialized ahead of the
    # symtab code.  The symtab observer is behind the python observers
    # in the execution queue so the cache flush executes /after/ us.
    @classmethod
    def flush_symbol_cache_callback(self, event):
        gdb.execute("maint flush-symbol-cache")

    def _new_objfile_callback(self, event):
        # GDB purposely copies the event list prior to calling the callbacks
        # If we remove an event from another handler, it will still be sent
        if self.completed:
            return

        result = self.check_ready()
        if not (result is None or result is False):
            completed = self.callback(result)
            if completed is True or completed is None:
                self.complete()

    def check_ready(self):
        """
        check_ready returns the value that will be passed to the callback.
        A return value other than None or False will be passed to the
        callback.
        """
        return True

    def callback(self, result):
        """
        The callback may return None, True, or False.  A return value of
        None or True indicates that the callback is completed and may
        be disconnected.  A return value of False indicates that the
        callback should stay connected for future use.

        Args:
            result: The result to pass to the callback
        """
        pass
