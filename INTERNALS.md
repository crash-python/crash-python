
# GDB

## Python contexts within GDB

Each time gdb enters the Python interpreter it establishes a context.
Part of the context includes what architecture gdb believes it is
debugging ('gdbarch') and that is passed into the context.  If anything
changes the gdbarch in that Python context, it won't be visible to any
subsequent Python code until a new session is established.

When gdb starts up on x86_64, it uses a gdbarch of i386 -- with 32-bit words
and pointers.  Only when we load an executable or target does it switch
to i386:x86_64.

The effect of this is that any code that relys on type information *must*
be executed in a separate context from the one that loaded the executable
and/or taret.  Otherwise, any built-in types that are pointers or `long`
based will use the 32-bit sizes.
