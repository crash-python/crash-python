# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, Iterator, List

from crash.exceptions import InvalidArgumentError, CorruptedError
from crash.types.list import list_for_each_entry
from crash.util import AddressSpecifier, get_typed_pointer
from crash.util.symbols import Types, Symvals, TypeCallbacks, SymbolCallbacks

import gdb

symvals = Symvals(['cgroup_roots', 'cgroup_subsys'])
types = Types([
    'struct cgroup',
    'struct cgroup_root',
    'struct cgroup_subsys',
    'struct cgrp_cset_link',
    'struct task_struct',
])

class Subsys:
    _subsys_names: Dict[int, str] = dict()
    _available_mask = 0

    @classmethod
    def init_subsys_ids(cls, subsys_enum: gdb.Symbol) -> None:
        suffix = '_cgrp_id'
        for k in subsys_enum.keys():
            if k == 'CGROUP_SUBSYS_COUNT':
                continue
            if subsys_enum[k].enumval in cls._subsys_names:
                raise InvalidArgumentError("Enum {} is not unique".format(subsys_enum.name))
            if not k.endswith(suffix):
                raise InvalidArgumentError("Enum {} has unknown names".format(subsys_enum.name))

            cls._subsys_names[subsys_enum[k].enumval] = k[:-len(suffix)]
            cls._available_mask |= (1 << subsys_enum[k].enumval)

    def for_each_subsys(self) -> Iterator[gdb.Value]:
        for ssid in self._subsys_names:
            yield symvals.cgroup_subsys[ssid].dereference()

    def subsys_mask_to_names(self, mask: int) -> List[str]:
        unknown = mask & ~self._available_mask
        if unknown:
            raise InvalidArgumentError(f"Mask contains unknown controllers {unknown:x}")

        ret = []
        for ssid in self._subsys_names:
            if mask & (1 << ssid):
                ret.append(self._subsys_names[ssid])
        return ret

_Subsys = Subsys()

def for_each_hierarchy() -> Iterator[gdb.Value]:
    # TODO should we factor in cgrp_dfl_visible?
    return list_for_each_entry(symvals.cgroup_roots,
                               types.cgroup_root_type, 'root_list')

def for_each_subsys() -> Iterator[gdb.Value]:
    return _Subsys.for_each_subsys()

def subsys_mask_to_names(mask: int) -> List[str]:
    return _Subsys.subsys_mask_to_names(mask)

def cgroup_from_root(task: gdb.Value, cgroup_root: gdb.Value) -> gdb.Value:
    cssset = task['cgroups'].dereference()
    for link in list_for_each_entry(cssset['cgrp_links'], types.cgrp_cset_link_type, 'cgrp_link'):
        if link['cgrp']['root'] == cgroup_root.address:
            return link['cgrp'].dereference()

    # TODO think about migrating tasks
    raise CorruptedError(
        "Task {int(task.address):016x} not under cgroup_root {int(cgroup_root.address):016x}}"
    )

def find_cgroup(addr: AddressSpecifier) -> gdb.Value:
    cgrp = get_typed_pointer(addr, types.cgroup_type).dereference()
    return cgrp

def for_each_cgroup_task(cgrp: gdb.Value) -> Iterator[gdb.Value]:
    # TODO migrating tasks?, zombies?
    for link in list_for_each_entry(cgrp['cset_links'], types.cgrp_cset_link_type, 'cset_link'):
        cssset = link['cset'].dereference()
        for task in list_for_each_entry(cssset['tasks'], types.task_struct_type, 'cg_list'):
            yield task

type_cbs = TypeCallbacks([('enum cgroup_subsys_id', Subsys.init_subsys_ids)])
