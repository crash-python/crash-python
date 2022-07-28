# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Any, Callable, List, Optional, TypeVar, Union

import abc

import gdb

Callback = Callable[[Any], Union[bool, None]]

OECType = TypeVar('OECType', bound='ObjfileEventCallback')

class CallbackCompleted(RuntimeError):
    """The callback has already been completed and is no longer valid"""
    def __init__(self, callback_obj: 'ObjfileEventCallback') -> None:
        msg = "Callback has already completed."
        super().__init__(msg)
        self.callback_obj = callback_obj

class ObjfileEventCallback(metaclass=abc.ABCMeta):
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

    _target_waitlist: List['ObjfileEventCallback'] = list()
    _pending_list: List['ObjfileEventCallback'] = list()
    _paused: bool = False
    _connected_to_objfile_callback: bool = False

    def check_target(self) -> bool:
        return isinstance(gdb.current_target(), gdb.LinuxKernelTarget)

    def __init__(self, wait_for_target: bool = True) -> None:
        self.completed = False
        self.connected = False
        self._waiting_for_target = wait_for_target and not self.check_target()

        if not self._connected_to_objfile_callback:
            # pylint: disable=no-member
            gdb.events.new_objfile.connect(self._new_objfile_callback)
            self._connected_to_objfile_callback = True

    # pylint: disable=unused-argument
    @classmethod
    def _new_objfile_callback(cls, event: gdb.NewObjFileEvent) -> None:
        cls.evaluate_all()

    @classmethod
    def target_ready(cls) -> None:
        for callback in cls._target_waitlist:
            callback.complete_wait_for_target()

        cls._target_waitlist[:] = list()
        cls._update_pending()

    @classmethod
    def evaluate_all(cls) -> None:
        if not cls._paused:
            for callback in cls._pending_list:
                callback.evaluate(False)
            cls._update_pending()

    @classmethod
    def pause(cls) -> None:
        cls._paused = True

    @classmethod
    def unpause(cls) -> None:
        cls._paused = False
        cls.evaluate_all()
    @classmethod
    def dump_lists(cls) -> None:
        print(f"Pending list: {[str(x) for x in ObjfileEventCallback._pending_list]}")
        print(f"Target waitlist: {[str(x) for x in ObjfileEventCallback._target_waitlist]}")

    def complete_wait_for_target(self) -> None:
        self._waiting_for_target = False
        self.evaluate(False)

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

        if not self._waiting_for_target:
            # We don't want to do lookups immediately if we don't have
            # an objfile.  It'll fail for any custom types but it can
            # also return builtin types that are eventually changed.
            if gdb.objfiles():
                self.evaluate()
        else:
            self._target_waitlist.append(self)

        if self.completed is False:
            self.connected = True
            self._pending_list.append(self)

        return self.completed

    @classmethod
    def _update_pending(cls) -> None:
        cls._pending_list[:] = [x for x in cls._pending_list if x.connected]

    def complete(self, update_now: bool = True) -> None:
        """
        Complete and disconnect this callback from the event system.

        Raises:
            :obj:`CallbackCompleted`: This callback has already been completed.
        """
        if not self.completed:
            self.completed = True
            if self.connected:
                self.connected = False
                if update_now:
                    self._update_pending()
        else:
            raise CallbackCompleted(self)

    def evaluate(self, update_now: bool = True) -> None:
        if not self._waiting_for_target:
            try:
                result = self.check_ready()
                if not (result is None or result is False):
                    completed = self.callback(result)
                    if completed is True or completed is None:
                        self.complete(update_now)
            except gdb.error:
                pass

    @abc.abstractmethod
    def check_ready(self) -> Any:
        """
        The method that derived classes implement for detecting when the
        conditions required to call the callback have been met.

        Returns:
            :obj:`object`: This method can return an arbitrary object.  It will
            be passed untouched to :meth:`callback` if the result is anything
            other than :obj:`None` or :obj:`False`.
        """
        pass

    @abc.abstractmethod
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
        pass

def target_ready() -> None:
    ObjfileEventCallback.target_ready()

def evaluate_all() -> None:
    ObjfileEventCallback.evaluate_all()

def pause_objfile_callbacks() -> None:
    ObjfileEventCallback.pause()

def unpause_objfile_callbacks() -> None:
    ObjfileEventCallback.unpause()

def dump_lists() -> None:
    ObjfileEventCallback.dump_lists()
