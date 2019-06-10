# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Callable, Any, Union, TypeVar, Optional

import gdb

Callback = Callable[[Any], Union[bool, None]]

OECType = TypeVar('OECType', bound='ObjfileEventCallback')

class CallbackCompleted(RuntimeError):
    """The callback has already been completed and is no longer valid"""
    def __init__(self, callback_obj: 'ObjfileEventCallback') -> None:
        msg = "Callback has already completed."
        super().__init__(msg)
        self.callback_obj = callback_obj

class ObjfileEventCallback:
    """
    A generic objfile callback class

    When GDB loads an objfile, it can perform callbacks.  These callbacks
    are triggered for every objfile loaded.  Once marked complete, the
    callback is removed so it doesn't trigger for future objfile loads.

    Derived classes need only implement the complete and check_ready
    methods.

    Consumers of this interface must also call :meth:`connect_callback` to
    connect the object to the callback infrastructure.
    """
    def __init__(self) -> None:
        self.completed = False
        self.connected = False

        self._setup_symbol_cache_flush_callback()

    def connect_callback(self) -> bool:
        """
        Connect this callback to the event system.

        Raises:
            :obj:`CallbackCompleted`: This callback has already been completed.
        """
        if self.completed:
            raise CallbackCompleted(self)

        if self.connected:
            return False

        self.connected = True

        # We don't want to do lookups immediately if we don't have
        # an objfile.  It'll fail for any custom types but it can
        # also return builtin types that are eventually changed.
        objfiles = gdb.objfiles()
        if objfiles:
            result = self.check_ready()
            if not (result is None or result is False):
                completed = self.callback(result)
                if completed is None:
                    completed = True
                self.completed = completed

        if self.completed is False:
            # pylint: disable=no-member
            gdb.events.new_objfile.connect(self._new_objfile_callback)

        return self.completed

    def complete(self) -> None:
        """
        Complete and disconnect this callback from the event system.

        Raises:
            :obj:`CallbackCompleted`: This callback has already been completed.
        """
        if not self.completed:
            # pylint: disable=no-member
            gdb.events.new_objfile.disconnect(self._new_objfile_callback)
            self.completed = True
            self.connected = False
        else:
            raise CallbackCompleted(self)

    _symbol_cache_flush_setup = False
    @classmethod
    def _setup_symbol_cache_flush_callback(cls) -> None:
        if not cls._symbol_cache_flush_setup:
            # pylint: disable=no-member
            gdb.events.new_objfile.connect(cls._flush_symbol_cache_callback)
            cls._symbol_cache_flush_setup = True


    # GDB does this itself, but Python is initialized ahead of the
    # symtab code.  The symtab observer is behind the python observers
    # in the execution queue so the cache flush executes /after/ us.
    @classmethod
    # pylint: disable=unused-argument
    def _flush_symbol_cache_callback(cls, event: gdb.NewObjFileEvent) -> None:
        gdb.execute("maint flush-symbol-cache")

    # pylint: disable=unused-argument
    def _new_objfile_callback(self, event: gdb.NewObjFileEvent) -> None:
        # GDB purposely copies the event list prior to calling the callbacks
        # If we remove an event from another handler, it will still be sent
        if self.completed:
            return

        result = self.check_ready()
        if not (result is None or result is False):
            completed = self.callback(result)
            if completed is True or completed is None:
                self.complete()

    def check_ready(self) -> Any:
        """
        The method that derived classes implement for detecting when the
        conditions required to call the callback have been met.

        Returns:
            :obj:`object`: This method can return an arbitrary object.  It will
            be passed untouched to :meth:`callback` if the result is anything
            other than :obj:`None` or :obj:`False`.
        """
        raise NotImplementedError("check_ready must be implemented by derived class.")

    def callback(self, result: Any) -> Optional[bool]:
        """
        The callback that derived classes implement for handling the
        sucessful result of :meth:`check_ready`.

        Args:
            result: The result returned from :meth:`check_ready`

        Returns:
            :obj:`None` or :obj:`bool`: If :obj:`None` or :obj:`True`,
            the callback succeeded and will be completed and removed.
            Otherwise, the callback will stay connected for future completion.
        """
        raise NotImplementedError("callback must be implemented by derived class.")
