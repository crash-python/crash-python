# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import argparse

from crash.cache.tasks import get_task
from crash.commands import Command, CommandError, ArgumentParser
from crash.subsystem.cgroup import (
    cgroup_from_root,
    find_cgroup,
    for_each_cgroup_task,
    for_each_hierarchy,
    for_each_subsys,
    subsys_mask_to_names,
)
from crash.subsystem.filesystem.kernfs import path_from_node
from crash.util import AddressSpecifier

class CgroupCommand(Command):

    def __init__(self, name: str) -> None:
        parser = ArgumentParser(prog=name)
        group = parser.add_mutually_exclusive_group()

        group.add_argument('-t', type=int, default=False,
                           help='Show task cgroup membership')
        group.add_argument('-g', type=ArgumentParser.address, default=False,
                           help='List all tasks in cgroup')
        group.add_argument('-s', type=int, default=False, # TODO cgroup arg type
                           help='Show cgroup attributes')
        group.add_argument('-c', type=str, nargs=2, default=False, # TODO cgroup arg type
                           help='Show controller attributes of cgroup')

        super().__init__(name, parser)

    def execute(self, args: argparse.Namespace) -> None:
        if args.t is not False:
            self.show_task(args.t)
        elif args.g is not False:
            self.show_cgroup_tasks(args.g)
        elif args.s:
            raise NotImplementedError("NI")
        elif args.c:
            raise NotImplementedError("NI")
        else:
            self.show_controllers()

    def show_controllers(self) -> None:
        """Output based on /proc/cgroups"""

        print("{:^16} {:^16} {:^16} {:^16} {:^16}".format(
            "subsys", "hierarchy_id", "num_cgroups", "cgroup_subsys",
            "cgroup_root"))
        for ss in for_each_subsys():
            print("{:<16} {:>16} {:>16} {:016x} {:016x}".format(
                ss['legacy_name'].string(),
                int(ss['root']['hierarchy_id']),
                int(ss['root']['nr_cgrps']['counter']),
                int(ss.address),
                int(ss['root'])
            ))

    def show_task(self, pid: int) -> None:
        try:
            ltask = get_task(pid)
            print("{:^12} {:^16} {:^32} {:^16} {:^20}".format(
                "hierarchy_id", "cgroup_root", "controllers/name", "cgroup", "path"
                ))
            for h in sorted(for_each_hierarchy(), key=lambda h: int(h['hierarchy_id'])):
                controllers = subsys_mask_to_names(h['subsys_mask'])
                if h['name'].string():
                    controllers.append("name={}".format(h['name'].string()))

                cgroup = cgroup_from_root(ltask.task_struct, h)

                print("{:>12} {:016x} {:<32} {:016x} {:<20}".format(
                    int(h['hierarchy_id']),
                    int(h.address),
                    ','.join(controllers),
                    int(cgroup.address),
                    path_from_node(cgroup['kn'].dereference())
                    ))

        except KeyError:
            raise CommandError("No such task with pid {}".format(pid)) from None

    def show_cgroup_tasks(self, addr: AddressSpecifier) -> None:
        cgrp = find_cgroup(addr)
        print("{:^10} {:^16}".format(
            "PID", "task_struct"
            ))
        for t in sorted(for_each_cgroup_task(cgrp), key=lambda t: int(t['pid'])):
            print("{:>10} {:016x}".format(
                int(t['pid']),
                int(t.address)
                ))


CgroupCommand("cgroup")
