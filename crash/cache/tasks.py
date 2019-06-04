# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.types.task import LinuxTask

tasks = {}

def cache_task(task: LinuxTask) -> None:
    tasks[int(task.task_struct['pid'])] = task

def get_task(pid: int) -> LinuxTask:
    return tasks[pid]

def drop_task(pid: int) -> None:
    del tasks[pid]
