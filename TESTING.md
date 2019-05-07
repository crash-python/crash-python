# Testing

## Summary

There are unit tests in the tests/ dir that are standalone and useful for
testing basic functionality.

There are unit tests in the kernel-tests dir that require configuration,
kernel images, debuginfo, and vmcores to use.

## Configuration

The configuration for each kernel/vmcore to be tested goes in a .ini file
with the following format.  All fields except kernel and vmcore are
optional, and defaults will be used.  A kernel missing debuginfo cannot
be used for testing.  Missing modules will mean module-specific tests
will be skipped.

```[test]
kernel=/path/to/kernel
vmcore=/path/to/vmcore
vmlinux_debuginfo=/path/to/vmlinux-debuginfo
modules=/path/to/modules
module_debuginfo_path=/path/to/module/debuginfo
root=/root/for/tree/searches```

The optional fields match those defined in crash.kernel.CrashKernel.

Example 1:
```[test]
kernel=/var/crash/2019-04-23-11:35/vmlinux-4.12.14-150.14-default.gz
vmcore=/var/crash/2019-04-23-11:35/vmcore```

In this example, the kernel and debuginfo packages are installed in the
default locations and will be searched automatically.

Example 2:
```[test]
kernel=/var/crash/2019-04-23-11:35/vmlinux-4.12.14-150.14-default.gz
vmcore=/var/crash/2019-04-23-11:35/vmcore
root=/var/cache/crash-setup/leap15/4.12.14-150.14-default
```

In this example, the kernel and debuginfo packages are installed under
/var/cache/crash-setup/leap15/4.12.14-150.14-default and so we only
specify a root directory.

## Running

The script `test-all.sh` when run with no options will execute only
the standalone tests.  The script takes a list of the .ini files
described above and will execute the kernel tests against those
configurations immediately after the standalone tests.

Example:
```sh test-all.sh kernel-test-configs/4.12.14-150.14-default.ini kernel-test-configs/5.1.0-rc7-vanilla.ini```
or
```sh test-all.sh kernel-test-configs/*.ini```

Each configuration will execute independently from one another.

