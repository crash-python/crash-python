# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Display process status information

::

  ps [-k|-u|-G][-s|-n][-p|-c|-t|-l|-a|-g|-r] [pid | taskp | command] ...``

DESCRIPTION
-----------

This command displays process status for selected, or all, processes
in the system.  If no arguments are entered, the process data is
is displayed for all processes.  Specific processes may be selected
by using the following identifier formats:


 ``pid`` -- a process PID

 ``taskp`` -- a hexadecimal ``struct task_struct`` pointer

 ``command`` --  a command name


If a command name is made up of letters that are all numerical values,
precede the name string with a ".  If the command string is
enclosed within "'" characters, then the encompassed string must be a
POSIX extended regular expression that will be used to match task names.

The process list may be further restricted by the following options:

      ``-k``  restrict the output to only kernel threads.

      ``-u``  restrict the output to only user tasks.

      ``-G``  display only the thread group leader in a thread group.

The process identifier types may be mixed.  For each task, the following
items are displayed:

  1. the process PID.
  2. the parent process PID.
  3. the CPU number that the task ran on last.
  4. the task_struct address or the kernel stack pointer of the process.
     (see -s option below)
  5. the task state (RU, IN, UN, ZO, ST, TR, DE, SW).
  6. the percentage of physical memory being used by this task.
  7. the virtual address size of this task in kilobytes.
  8. the resident set size of this task in kilobytes.
  9. the command name.

The default output shows the task_struct address of each process under a
column titled "``TASK``".  This can be changed to show the kernel stack
pointer under a column titled "``KSTACKP``".

     ``-s``  replace the ``TASK`` column with the ``KSTACKP`` column.

On SMP machines, the active task on each CPU will be highlighted by an
angle bracket (">") preceding its information.

Alternatively, information regarding parent-child relationships,
per-task time usage data, argument/environment data, thread groups,
or resource limits may be displayed:

     ``-p``  display the parental hierarchy of selected, or all, tasks.

     ``-c``  display the children of selected, or all, tasks.

     ``-t``  display the task run time, start time, and cumulative user and system times.

     ``-l``  display the task last_run or timestamp value, whichever applies, of selected, or all, tasks; the list is sorted with the most recently-run task (largest last_run/timestamp) shown first, followed by the task's current state.

     ``-a``  display the command line arguments and environment strings of selected, or all, user-mode tasks.

     ``-g``  display tasks by thread group, of selected, or all, tasks.

     ``-r``  display resource limits (rlimits) of selected, or all, tasks.

     ``-n``  display gdb thread number


EXAMPLES
--------

Show the process status of all current tasks:

::

  py-crash> ps
     PID    PPID  CPU   TASK    ST  %MEM   VSZ   RSS  COMM
  >     0      0   3  c024c000  RU   0.0     0     0  [swapper]
  >     0      0   0  c0dce000  RU   0.0     0     0  [swapper]
        0      0   1  c0fa8000  RU   0.0     0     0  [swapper]
  >     0      0   2  c009a000  RU   0.0     0     0  [swapper]
        1      0   1  c0098000  IN   0.0  1096   476  init
        2      1   1  c0090000  IN   0.0     0     0  [kflushd]
        3      1   1  c000e000  IN   0.0     0     0  [kpiod]
        4      1   3  c000c000  IN   0.0     0     0  [kswapd]
        5      1   1  c0008000  IN   0.0     0     0  [mdrecoveryd]
      253      1   2  fbc4c000  IN   0.0  1088   376  portmap
      268      1   2  fbc82000  IN   0.1  1232   504  ypbind
      274    268   2  fa984000  IN   0.1  1260   556  ypbind
      321      1   1  fabf6000  IN   0.1  1264   608  syslogd
      332      1   1  fa9be000  RU   0.1  1364   736  klogd
      346      1   2  fae88000  IN   0.0  1112   472  atd
      360      1   2  faeb2000  IN   0.1  1284   592  crond
      378      1   2  fafd6000  IN   0.1  1236   560  inetd
      392      1   0  fb710000  IN   0.1  2264  1468  named
      406      1   3  fb768000  IN   0.1  1284   560  lpd
      423      1   1  fb8ac000  IN   0.1  1128   528  rpc.statd
      434      1   2  fb75a000  IN   0.0  1072   376  rpc.rquotad
      445      1   2  fb4a4000  IN   0.0  1132   456  rpc.mountd
      460      1   1  fa938000  IN   0.0     0     0  [nfsd]
      461      1   1  faa86000  IN   0.0     0     0  [nfsd]
      462      1   0  fac48000  IN   0.0     0     0  [nfsd]
      463      1   0  fb4ca000  IN   0.0     0     0  [nfsd]
      464      1   0  fb4c8000  IN   0.0     0     0  [nfsd]
      465      1   2  fba6e000  IN   0.0     0     0  [nfsd]
      466      1   1  fba6c000  IN   0.0     0     0  [nfsd]
      467      1   2  fac04000  IN   0.0     0     0  [nfsd]
      468    461   2  fa93a000  IN   0.0     0     0  [lockd]
      469    468   2  fa93e000  IN   0.0     0     0  [rpciod]
      486      1   0  fab54000  IN   0.1  1596   880  amd
      523      1   2  fa84e000  IN   0.1  1884  1128  sendmail
      538      1   0  fa82c000  IN   0.0  1112   416  gpm
      552      1   3  fa70a000  IN   0.1  2384  1220  httpd
      556    552   3  fa776000  IN   0.1  2572  1352  httpd
      557    552   2  faba4000  IN   0.1  2572  1352  httpd
      558    552   1  fa802000  IN   0.1  2572  1352  httpd
      559    552   3  fa6ee000  IN   0.1  2572  1352  httpd
      560    552   3  fa700000  IN   0.1  2572  1352  httpd
      561    552   0  fa6f0000  IN   0.1  2572  1352  httpd
      562    552   3  fa6ea000  IN   0.1  2572  1352  httpd
      563    552   0  fa67c000  IN   0.1  2572  1352  httpd
      564    552   3  fa674000  IN   0.1  2572  1352  httpd
      565    552   3  fa66a000  IN   0.1  2572  1352  httpd
      582      1   2  fa402000  IN   0.2  2968  1916  xfs
      633      1   2  fa1ec000  IN   0.2  5512  2248  innd
      636      1   3  fa088000  IN   0.1  2536   804  actived
      676      1   0  fa840000  IN   0.0  1060   384  mingetty
      677      1   1  fa590000  IN   0.0  1060   384  mingetty
      678      1   2  fa3b8000  IN   0.0  1060   384  mingetty
      679      1   0  fa5b8000  IN   0.0  1060   384  mingetty
      680      1   1  fa3a4000  IN   0.0  1060   384  mingetty
      681      1   2  fa30a000  IN   0.0  1060   384  mingetty
      683      1   3  fa5d8000  IN   0.0  1052   280  update
      686    378   1  fa3aa000  IN   0.1  2320  1136  in.rlogind
      687    686   2  f9e52000  IN   0.1  2136  1000  login
      688    687   0  f9dec000  IN   0.1  1732   976  bash
  >   700    688   1  f9d62000  RU   0.0  1048   256  gen12

Display the parental hierarchy of the "crash" process on a live system:

::

  py-crash> ps -p 4249
  PID: 0      TASK: c0252000  CPU: 0   COMMAND: "swapper"
  PID: 1      TASK: c009a000  CPU: 1   COMMAND: "init"
  PID: 632    TASK: c73b6000  CPU: 1   COMMAND: "prefdm"
  PID: 637    TASK: c5a4a000  CPU: 1   COMMAND: "prefdm"
  PID: 649    TASK: c179a000  CPU: 0   COMMAND: "kwm"
  PID: 683    TASK: c1164000  CPU: 0   COMMAND: "kfm"
  PID: 1186   TASK: c165a000  CPU: 0   COMMAND: "xterm"
  PID: 1188   TASK: c705e000  CPU: 1   COMMAND: "bash"
  PID: 4249   TASK: c6b9a000  CPU: 0   COMMAND: "crash"

Display all children of the "kwm" window manager:

::

  py-crash> ps -c kwm
    PID: 649    TASK: c179a000  CPU: 0   COMMAND: "kwm"
    PID: 682    TASK: c2d58000  CPU: 1   COMMAND: "kwmsound"
    PID: 683    TASK: c1164000  CPU: 1   COMMAND: "kfm"
    PID: 685    TASK: c053c000  CPU: 0   COMMAND: "krootwm"
    PID: 686    TASK: c13fa000  CPU: 0   COMMAND: "kpanel"
    PID: 687    TASK: c13f0000  CPU: 1   COMMAND: "kbgndwm"

Display all threads in a firefox session:

::

  py-crash> ps firefox
     PID    PPID  CPU       TASK        ST  %MEM     VSZ    RSS  COMM
    21273  21256   6  ffff81003ec15080  IN  46.3 1138276 484364  firefox
    21276  21256   6  ffff81003f49e7e0  IN  46.3 1138276 484364  firefox
    21280  21256   0  ffff81003ec1d7e0  IN  46.3 1138276 484364  firefox
    21286  21256   6  ffff81000b0d1820  IN  46.3 1138276 484364  firefox
    21287  21256   2  ffff81000b0d10c0  IN  46.3 1138276 484364  firefox
    26975  21256   5  ffff81003b5c1820  IN  46.3 1138276 484364  firefox
    26976  21256   5  ffff810023232820  IN  46.3 1138276 484364  firefox
    26977  21256   4  ffff810021a11820  IN  46.3 1138276 484364  firefox
    26978  21256   5  ffff810003159040  IN  46.3 1138276 484364  firefox
    26979  21256   5  ffff81003a058820  IN  46.3 1138276 484364  firefox

Display only the thread group leader in the firefox session:

::

  py-crash> ps -G firefox
     PID    PPID  CPU       TASK        ST  %MEM     VSZ    RSS  COMM
    21273  21256   0  ffff81003ec15080  IN  46.3 1138276 484364  firefox

Show the time usage data for pid 10318:

::

  py-crash> ps -t 10318
  PID: 10318  TASK: f7b85550  CPU: 5   COMMAND: "bash"
      RUN TIME: 1 days, 01:35:32
    START TIME: 5209
         UTIME: 95
         STIME: 57

Show the process status of PID 1, task f9dec000, and all nfsd tasks:

::

  py-crash> ps 1 f9dec000 nfsd
     PID    PPID  CPU   TASK    ST  %MEM   VSZ   RSS  COMM
        1      0   1  c0098000  IN   0.0  1096   476  init
      688    687   0  f9dec000  IN   0.1  1732   976  bash
      460      1   1  fa938000  IN   0.0     0     0  [nfsd]
      461      1   1  faa86000  IN   0.0     0     0  [nfsd]
      462      1   0  fac48000  IN   0.0     0     0  [nfsd]
      463      1   0  fb4ca000  IN   0.0     0     0  [nfsd]
      464      1   0  fb4c8000  IN   0.0     0     0  [nfsd]
      465      1   2  fba6e000  IN   0.0     0     0  [nfsd]
      466      1   1  fba6c000  IN   0.0     0     0  [nfsd]
      467      1   2  fac04000  IN   0.0     0     0  [nfsd]

Show all kernel threads:

::

  py-crash> ps -k
     PID    PPID  CPU   TASK    ST  %MEM   VSZ   RSS  COMM
        0      0   1  c0fac000  RU   0.0     0     0  [swapper]
        0      0   0  c0252000  RU   0.0     0     0  [swapper]
        2      1   1  c0fa0000  IN   0.0     0     0  [kflushd]
        3      1   1  c03de000  IN   0.0     0     0  [kpiod]
        4      1   1  c03dc000  IN   0.0     0     0  [kswapd]
        5      1   0  c0092000  IN   0.0     0     0  [mdrecoveryd]
      336      1   0  c4a9a000  IN   0.0     0     0  [rpciod]
      337      1   0  c4830000  IN   0.0     0     0  [lockd]
      487      1   1  c4ba6000  IN   0.0     0     0  [nfsd]
      488      1   0  c18c6000  IN   0.0     0     0  [nfsd]
      489      1   0  c0cac000  IN   0.0     0     0  [nfsd]
      490      1   0  c056a000  IN   0.0     0     0  [nfsd]
      491      1   0  c0860000  IN   0.0     0     0  [nfsd]
      492      1   1  c0254000  IN   0.0     0     0  [nfsd]
      493      1   0  c0a86000  IN   0.0     0     0  [nfsd]
      494      1   0  c0968000  IN   0.0     0     0  [nfsd]

Show all tasks sorted by their task_struct's last_run or timestamp value,
whichever applies:

::

  py-crash> ps -l
  [280195] [RU]  PID: 2      TASK: c1468000  CPU: 0   COMMAND: "keventd"
  [280195] [IN]  PID: 1986   TASK: c5af4000  CPU: 0   COMMAND: "sshd"
  [280195] [IN]  PID: 2039   TASK: c58e6000  CPU: 0   COMMAND: "sshd"
  [280195] [RU]  PID: 2044   TASK: c5554000  CPU: 0   COMMAND: "bash"
  [280195] [RU]  PID: 2289   TASK: c70c0000  CPU: 0   COMMAND: "s"
  [280190] [IN]  PID: 1621   TASK: c54f8000  CPU: 0   COMMAND: "cupsd"
  [280184] [IN]  PID: 5      TASK: c154c000  CPU: 0   COMMAND: "kswapd"
  [280184] [IN]  PID: 6      TASK: c7ff6000  CPU: 0   COMMAND: "kscand"
  [280170] [IN]  PID: 0      TASK: c038e000  CPU: 0   COMMAND: "swapper"
  [280166] [IN]  PID: 2106   TASK: c0c0c000  CPU: 0   COMMAND: "sshd"
  [280166] [IN]  PID: 2162   TASK: c03a4000  CPU: 0   COMMAND: "vmstat"
  [280160] [IN]  PID: 1      TASK: c154a000  CPU: 0   COMMAND: "init"
  [280131] [IN]  PID: 3      TASK: c11ce000  CPU: 0   COMMAND: "kapmd"
  [280117] [IN]  PID: 1568   TASK: c5a8c000  CPU: 0   COMMAND: "smartd"
  [280103] [IN]  PID: 1694   TASK: c4c66000  CPU: 0   COMMAND: "ntpd"
  [280060] [IN]  PID: 8      TASK: c7ff2000  CPU: 0   COMMAND: "kupdated"
  [279767] [IN]  PID: 1720   TASK: c4608000  CPU: 0   COMMAND: "sendmail"
  [279060] [IN]  PID: 13     TASK: c69f4000  CPU: 0   COMMAND: "kjournald"
  [278657] [IN]  PID: 1523   TASK: c5ad4000  CPU: 0   COMMAND: "ypbind"
  [277712] [IN]  PID: 2163   TASK: c06e0000  CPU: 0   COMMAND: "sshd"
  [277711] [IN]  PID: 2244   TASK: c4cdc000  CPU: 0   COMMAND: "ssh"
  [277261] [IN]  PID: 1391   TASK: c5d8e000  CPU: 0   COMMAND: "syslogd"
  [276837] [IN]  PID: 1990   TASK: c58d8000  CPU: 0   COMMAND: "bash"
  [276802] [IN]  PID: 1853   TASK: c3828000  CPU: 0   COMMAND: "atd"
  [276496] [IN]  PID: 1749   TASK: c4480000  CPU: 0   COMMAND: "cannaserver"
  [274931] [IN]  PID: 1760   TASK: c43ac000  CPU: 0   COMMAND: "crond"
  [246773] [IN]  PID: 1844   TASK: c38d8000  CPU: 0   COMMAND: "xfs"
  [125620] [IN]  PID: 2170   TASK: c48dc000  CPU: 0   COMMAND: "bash"
  [119059] [IN]  PID: 1033   TASK: c64be000  CPU: 0   COMMAND: "kjournald"
  [110916] [IN]  PID: 1663   TASK: c528a000  CPU: 0   COMMAND: "sshd"
  [ 86122] [IN]  PID: 2112   TASK: c0da6000  CPU: 0   COMMAND: "bash"
  [ 13637] [IN]  PID: 1891   TASK: c67ae000  CPU: 0   COMMAND: "sshd"
  [ 13636] [IN]  PID: 1894   TASK: c38ec000  CPU: 0   COMMAND: "bash"
  [  7662] [IN]  PID: 1885   TASK: c6478000  CPU: 0   COMMAND: "mingetty"
  [  7662] [IN]  PID: 1886   TASK: c62da000  CPU: 0   COMMAND: "mingetty"
  [  7662] [IN]  PID: 1887   TASK: c5f8c000  CPU: 0   COMMAND: "mingetty"
  [  7662] [IN]  PID: 1888   TASK: c5f88000  CPU: 0   COMMAND: "mingetty"
  [  7662] [IN]  PID: 1889   TASK: c5f86000  CPU: 0   COMMAND: "mingetty"
  [  7662] [IN]  PID: 1890   TASK: c6424000  CPU: 0   COMMAND: "mingetty"
  [  7661] [IN]  PID: 4      TASK: c154e000  CPU: 0   COMMAND: "ksoftirqd/0"
  [  7595] [IN]  PID: 1872   TASK: c2e7e000  CPU: 0   COMMAND: "inventory.pl"
  [  6617] [IN]  PID: 1771   TASK: c435a000  CPU: 0   COMMAND: "jserver"
  [  6307] [IN]  PID: 1739   TASK: c48f8000  CPU: 0   COMMAND: "gpm"
  [  6285] [IN]  PID: 1729   TASK: c4552000  CPU: 0   COMMAND: "sendmail"
  [  6009] [IN]  PID: 1395   TASK: c6344000  CPU: 0   COMMAND: "klogd"
  [  5820] [IN]  PID: 1677   TASK: c4d74000  CPU: 0   COMMAND: "xinetd"
  [  5719] [IN]  PID: 1422   TASK: c5d04000  CPU: 0   COMMAND: "portmap"
  [  4633] [IN]  PID: 1509   TASK: c5ed4000  CPU: 0   COMMAND: "apmd"
  [  4529] [IN]  PID: 1520   TASK: c5d98000  CPU: 0   COMMAND: "ypbind"
  [  4515] [IN]  PID: 1522   TASK: c5d32000  CPU: 0   COMMAND: "ypbind"
  [  4373] [IN]  PID: 1441   TASK: c5d48000  CPU: 0   COMMAND: "rpc.statd"
  [  4210] [IN]  PID: 1352   TASK: c5b30000  CPU: 0   COMMAND: "dhclient"
  [  1184] [IN]  PID: 71     TASK: c65b6000  CPU: 0   COMMAND: "khubd"
  [   434] [IN]  PID: 9      TASK: c11de000  CPU: 0   COMMAND: "mdrecoveryd"
  [    48] [IN]  PID: 7      TASK: c7ff4000  CPU: 0   COMMAND: "bdflush"

Show the kernel stack pointer of each user task:

::

  py-crash> ps -us
     PID    PPID  CPU  KSTACKP  ST  %MEM   VSZ   RSS  COMM
        1      0   0  c009bedc  IN   0.0  1096    52  init
      239      1   0  c15e7ed8  IN   0.2  1332   224  pump
      280      1   1  c7cbdedc  IN   0.2  1092   208  portmap
      295      1   0  c7481edc  IN   0.0  1232     0  ypbind
      301    295   0  c7c7bf28  IN   0.1  1260   124  ypbind
      376      1   1  c5053f28  IN   0.0  1316    40  automount
      381      1   0  c34ddf28  IN   0.2  1316   224  automount
      391      1   1  c2777f28  IN   0.2  1316   224  automount
  ...

Display the argument and environment data for the automount task:

::

  py-crash> ps -a automount
  PID: 3948   TASK: f722ee30  CPU: 0   COMMAND: "automount"
  ARG: /usr/sbin/automount --timeout=60 /net program /etc/auto.net
  ENV: SELINUX_INIT=YES
       CONSOLE=/dev/console
       TERM=linux
       INIT_VERSION=sysvinit-2.85
       PATH=/sbin:/usr/sbin:/bin:/usr/bin
       LC_MESSAGES=en_US
       RUNLEVEL=3
       runlevel=3
       PWD=/
       LANG=ja_JP.UTF-8
       PREVLEVEL=N
       previous=N
       HOME=/
       SHLVL=2
       _=/usr/sbin/automount

Display the tasks in the thread group containing task c20ab0b0:

::

  py-crash> ps -g c20ab0b0
  PID: 6425   TASK: f72f50b0  CPU: 0   COMMAND: "firefox-bin"
    PID: 6516   TASK: f71bf1b0  CPU: 0   COMMAND: "firefox-bin"
    PID: 6518   TASK: d394b930  CPU: 0   COMMAND: "firefox-bin"
    PID: 6520   TASK: c20aa030  CPU: 0   COMMAND: "firefox-bin"
    PID: 6523   TASK: c20ab0b0  CPU: 0   COMMAND: "firefox-bin"
    PID: 6614   TASK: f1f181b0  CPU: 0   COMMAND: "firefox-bin"

Display the tasks in the thread group for each instance of the
program named "multi-thread":

::

  py-crash> ps -g multi-thread
  PID: 2522   TASK: 1003f0dc7f0       CPU: 1   COMMAND: "multi-thread"
    PID: 2523   TASK: 10037b13030       CPU: 1   COMMAND: "multi-thread"
    PID: 2524   TASK: 1003e064030       CPU: 1   COMMAND: "multi-thread"
    PID: 2525   TASK: 1003e13a7f0       CPU: 1   COMMAND: "multi-thread"

  PID: 2526   TASK: 1002f82b7f0       CPU: 1   COMMAND: "multi-thread"
    PID: 2527   TASK: 1003e1737f0       CPU: 1   COMMAND: "multi-thread"
    PID: 2528   TASK: 10035b4b7f0       CPU: 1   COMMAND: "multi-thread"
    PID: 2529   TASK: 1003f0c37f0       CPU: 1   COMMAND: "multi-thread"
    PID: 2530   TASK: 10035597030       CPU: 1   COMMAND: "multi-thread"
    PID: 2531   TASK: 100184be7f0       CPU: 1   COMMAND: "multi-thread"

Display the resource limits of "bash" task 13896:

::

  py-crash> ps -r 13896
  PID: 13896  TASK: cf402000  CPU: 0   COMMAND: "bash"
     RLIMIT     CURRENT       MAXIMUM
        CPU   (unlimited)   (unlimited)
      FSIZE   (unlimited)   (unlimited)
       DATA   (unlimited)   (unlimited)
      STACK    10485760     (unlimited)
       CORE   (unlimited)   (unlimited)
        RSS   (unlimited)   (unlimited)
      NPROC      4091          4091
     NOFILE      1024          1024
    MEMLOCK      4096          4096
         AS   (unlimited)   (unlimited)
      LOCKS   (unlimited)   (unlimited)

Search for task names matching a POSIX regular expression:

::

   py-crash> ps 'migration*'
      PID    PPID  CPU       TASK        ST  %MEM    VSZ    RSS  COMM
         8      2   0  ffff8802128a2e20  IN   0.0      0      0  [migration/0]
        10      2   1  ffff880212969710  IN   0.0      0      0  [migration/1]
        15      2   2  ffff880212989710  IN   0.0      0      0  [migration/2]
        20      2   3  ffff8802129a9710  IN   0.0      0      0  [migration/3]
"""

from typing import Pattern, Optional, Callable, Dict

import argparse
import fnmatch
import re

from crash.commands import Command, ArgumentParser
from crash.commands import CommandError
from crash.types.task import LinuxTask, TaskStateFlags as TF

import gdb

class TaskFormat:
    """
    This class is responsible for converting the arguments into formatting
    rules.
    """
    def __init__(self, args: argparse.Namespace,
                 regex: Optional[Pattern[str]]) -> None:
        self.sort = lambda x: x.info.task_pid()
        self._filter: Callable[[LinuxTask], bool] = lambda x: True
        self._format_one_task = self._format_common_line
        self._regex = regex

        if args.s:
            self._format_header = self._format_stack_header
            self._format_column4 = self._format_stack_address
        elif args.n:
            self._format_header = self._format_threadnum_header
            self._format_column4 = self._format_thread_num
        else:
            self._format_header = self._format_task_header
            self._format_column4 = self._format_task_address

        if args.k:
            self._filter = self._is_kernel_thread
        elif args.u:
            self._filter = self._is_user_task
        elif args.G:
            self._filter = self._is_thread_group_leader

        if args.l:
            self.sort = lambda x: -x.info.last_run()
            self._format_one_task = self._format_last_run
            self._format_header = lambda: ""

    def _format_generic_header(self, col4name: str, col4width: int) -> str:
        header = f"    PID    PPID  CPU {col4name:^{col4width}}  ST  %MEM     "
        header += "VSZ    RSS  COMM"

        return header

    def _format_stack_header(self) -> str:
        return self._format_generic_header("KSTACK", 16)

    def _format_stack_address(self, task: LinuxTask) -> str:
        addr = int(task.get_stack_pointer())
        return f"{addr:16x}"

    def _format_task_header(self) ->str:
        return self._format_generic_header("TASK", 16)

    def _format_task_address(self, task: LinuxTask) -> str:
        addr = int(task.task_struct.address)
        return f"{addr:16x}"

    def _format_threadnum_header(self) -> str:
        return self._format_generic_header("THREAD#", 7)

    def _format_thread_num(self, task: LinuxTask) -> str:
        return f"{task.thread.num:7d}"

    def _is_kernel_thread(self, task: LinuxTask) -> bool:
        return task.is_kernel_task()

    def _is_user_task(self, task: LinuxTask) -> bool:
        return not self._is_kernel_thread(task)

    def _is_thread_group_leader(self, task: LinuxTask) -> bool:
        return task.is_thread_group_leader()

    def _format_common_line(self, task: LinuxTask, state: str) -> str:
        pid = task.task_pid()
        parent_pid = task.parent_pid()
        last_cpu = task.get_last_cpu()
        name = task.task_name()

        # This needs adaptation for page size != 4k
        total_vm = task.total_vm * 4096 // 1024
        rss = task.rss * 4096 // 1024

        if task.active:
            active = ">"
        else:
            active = " "

        line = f"{active} {pid:>5}   {parent_pid:>5}  {last_cpu:>3}  "
        line += self._format_column4(task)
        line += f" {state:3}  {0:.1f} {total_vm:7d} {rss:6d}  {name}"

        return line

    def _format_last_run(self, task: LinuxTask, state: str) -> str:
        pid = task.task_pid()
        addr = task.task_address()
        cpu = task.get_last_cpu()
        name = task.task_name()
        if task.active:
            cpu = task.cpu

        line = f"[{task.last_run():d}] [{state}]  PID: {pid:-5d}  "
        line += f"TASK: {addr:x} CPU: {cpu:>2d}  COMMAND: \"{name}\""

        return line

    def should_print_task(self, task: LinuxTask) -> bool:
        """
        Given optional filters and regex as part of the parent
        object, return whether a task passes the criteria to be
        printed.

        Args:
            task (LinuxTask): The task under consideration

        Returns:
            bool: Whether this task should be printed
        """
        if self._filter(task) is False:
            return False

        if self._regex and not self._regex.match(task.task_name()):
            return False

        return True

    def format_one_task(self, task: LinuxTask, state: str) -> str:
        """
        Given the formatting rules, produce the output line for this task.

        Args:
            task (LinuxTask): The task to be printed

        Returns:
            str: The ps output line for this task
        """
        return self._format_one_task(task, state)

    def format_header(self) -> str:
        """
        Return the header for this output object

        Returns:
            str: The header for this type of ps output
        """
        return self._format_header()

class _Parser(ArgumentParser):
    def format_usage(self) -> str:
        return \
        "ps [-k|-u|-G][-s][-p|-c|-t|-l|-a|-g|-r] [pid | taskp | command] ...\n"

class PSCommand(Command):
    """display process status information"""
    def __init__(self) -> None:
        parser = _Parser(prog="ps")

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-k', action='store_true', default=False)
        group.add_argument('-u', action='store_true', default=False)
        group.add_argument('-G', action='store_true', default=False)

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-s', action='store_true', default=False)
        group.add_argument('-n', action='store_true', default=False)

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-p', action='store_true', default=False)
        group.add_argument('-c', action='store_true', default=False)
        group.add_argument('-t', action='store_true', default=False)
        group.add_argument('-l', action='store_true', default=False)
        group.add_argument('-a', action='store_true', default=False)
        group.add_argument('-g', action='store_true', default=False)
        group.add_argument('-r', action='store_true', default=False)

        parser.add_argument('args', nargs=argparse.REMAINDER)

        Command.__init__(self, "ps", parser)

        self.task_states: Dict[int, str] = dict()

    def task_state_string(self, task: LinuxTask) -> str:
        state = task.task_state()
        buf = ""

        for bits in sorted(self.task_states.keys(), reverse=True):
            if (state & bits) == bits:
                buf = self.task_states[bits]
                break
        if state & TF.TASK_DEAD and task.maybe_dead():
            buf = self.task_states[TF.TASK_DEAD]

        if not buf:
            print(f"Unknown state {state} found")

        return buf

    def setup_task_states(self) -> None:
        self.task_states = {
            TF.TASK_RUNNING         : "RU",
            TF.TASK_INTERRUPTIBLE   : "IN",
            TF.TASK_UNINTERRUPTIBLE : "UN",
            TF.EXIT_ZOMBIE          : "ZO",
            TF.TASK_STOPPED         : "ST",
        }

        if TF.has_flag('TASK_SWAPPING'):
            self.task_states[TF.TASK_SWAPPING] = "SW"
        if TF.has_flag('TASK_DEAD'):
            self.task_states[TF.TASK_DEAD] = "DE"
        if TF.has_flag('TASK_TRACING_STOPPED'):
            self.task_states[TF.TASK_TRACING_STOPPED] = "TR"
        if TF.has_flag('TASK_IDLE'):
            self.task_states[TF.TASK_IDLE] = "ID"

    def execute(self, args: argparse.Namespace) -> None:
        # Unimplemented
        if args.p or args.c or args.t or args.a or args.g or args.r:
            raise CommandError("Support for the -p, -c, -t, -a, -g, and -r options is unimplemented.")

        if not self.task_states:
            self.setup_task_states()

        regex = None
        if args.args:
            regex = re.compile(fnmatch.translate(args.args[0]))

        taskformat = TaskFormat(args, regex)

        count = 0
        header = taskformat.format_header()
        for thread in sorted(gdb.selected_inferior().threads(),
                             key=taskformat.sort):
            task = thread.info
            if task:
                if not taskformat.should_print_task(task):
                    continue

                if header:
                    print(header)
                    header = ""

                task.update_mem_usage()
                state = self.task_state_string(task)
                line = taskformat.format_one_task(task, state)
                print(line)
                count += 1

        if count == 0:
            if regex:
                print(f"No matches for {args.args[0]}.")
            else:
                raise CommandError("Unfiltered output has no matches. BUG?")

PSCommand()
