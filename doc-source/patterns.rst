Patterns
========

Optional error handling
-----------------------

In some cases it may be desirable to keep exception handling in a helper
that returns :obj:`None` on error.  In the past, the project used an
optional ``error`` argument that defaulted to :obj:`True` that indicated
that exceptions should be raised.  Callers could pass ``error=False`` to
instruct the function to return :obj:`None` instead.

With Python's
`typing <https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep526>`_
annotations, these routines must be annotated as returning an
`Optional <https://mypy.readthedocs.io/en/latest/kinds_of_types.html?highlight=optional#optional-types-and-the-none-type>`_
value.  While the
`@overload <https://mypy.readthedocs.io/en/latest/more_types.html?highlight=overload#function-overloading>`_
decorator allows us to associate return types with specific argument types
and counts, there is no way to associate a return type with specific
argument `values`, like ``error=False``.

A function annotated as returning an ``Optional`` value affects the implied
types of the variables used to assign the result.  Every caller of such
a routine would need to check the result against :obj:`None` in order to
drop the ``Optional`` annotation from the type.  Even when we know the
function `cannot` return :obj:`None` when passed ``error=True``.

The way we handle this is to have separate functions for each case
so that callers which will never have a :obj:`None` value returned
do not need to check it.

Here are a few examples:


Function raises its own exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: py

    from typing import Optional

    import gdb

    def new_routine(val: gdb.Value) -> str:
        if some_condition:
            raise RuntimeError("something bad happened")

        return val.string()

    def new_routine_safe(val: gdb.Value) -> Optional[str]:
        try:
            return new_routine(val)
        except RuntimeError:
            return None


Function calls functions that raise optional exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: py

    from typing import Optional

    import gdb

    def some_existing_routine(val: gdb.Value, error: bool = True) -> Optional[str]:
        if some_condition:
            if error:
                raise RuntimeError("something bad happened")
            return None

        return val.string()

    def new_routine(val: gdb.Value) -> str:
        print("do something")

        ret = some_existing_routine(val)

	# This is required to drop the Optional annotation
        if ret is None:
            raise RuntimeError("some_existing_routine can't return None")
        return ret

    def new_routine_safe(val: gdb.Value) -> Optional[str]:
        return some_existing_routine(val, False)
