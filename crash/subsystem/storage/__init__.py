# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Callable, Iterable

import gdb
from gdb.types import get_basic_type

from crash.util import container_of, struct_has_member, InvalidComponentError
from crash.util.symbols import Types, Symvals, SymbolCallbacks, TypeCallbacks
from crash.types.classdev import for_each_class_device
from crash.exceptions import DelayedAttributeError, InvalidArgumentError
from crash.cache.syscache import kernel, jiffies_to_msec

types = Types(['struct gendisk', 'struct hd_struct', 'struct device',
               'struct device_type', 'struct bdev_inode', 'struct block_device',
               'struct request_queue', 'struct request', 'enum req_flag_bits',
               'enum mq_rq_state', 'enum rq_atomic_flags'])
symvals = Symvals(['block_class', 'blockdev_superblock', 'disk_type',
                   'part_type'])
READ = 0
WRITE = 1

# Values will be filled in via callback.  These are declared here to honor
# imports for lint.
REQ_FUA: int
REQ_PREFLUSH: int
REQ_STARTED: int
REQ_SYNC: int

def dev_to_bdev(dev: gdb.Value) -> gdb.Value:
    """
    Converts a ``struct device'' that is embedded in a ``struct block_device``
    back to the ``struct block_device``.

    Args:
        dev: A ``struct device'' contained within a ``struct block_device``.
            The vlaue must be of type ``struct device``.

    Returns:
        :obj:`gdb.Value`: The converted block device.  The value is of type
        ``struct block_device``.
    """
    return container_of(dev, types.block_device_type, 'bd_device')

def dev_to_gendisk(dev: gdb.Value) -> gdb.Value:
    """
    Converts a ``struct device`` that is embedded in a ``struct gendisk``
    back to the ``struct gendisk``.

    Args:
        dev: A ``struct device`` contained within a ``struct gendisk``.
            The value must be of type ``struct device``.

    Returns:
        :obj:`gdb.Value`: The converted gendisk.  The value is of type
        ``struct gendisk``.
    """
    try:
        return container_of(dev, types.gendisk_type, 'part0.__dev')
    except InvalidComponentError:
        return dev_to_bdev(dev)['bd_disk']

def dev_to_part(dev: gdb.Value) -> gdb.Value:
    """
    Converts a ``struct device`` that is embedded in a ``struct hd_struct``
    back to the ``struct hd_struct``.

    Args:
        dev: A ``struct device`` embedded within a ``struct hd_struct``.  The
            value must be of type ``struct device``.

    Returns:
        :obj:`gdb.Value`: The converted ``struct hd_struct``.  The value is of
        type ``struct hd_struct``.

    """
    return container_of(dev, types.hd_struct_type, '__dev')

def gendisk_to_dev(gendisk: gdb.Value) -> gdb.Value:
    """
    Converts a ``struct gendisk`` that embeds a ``struct device`` to
    the ``struct device``.

    Args:
        dev: A ``struct gendisk`` that embeds a ``struct device``.  The
            value must be of type ``struct device``.

    Returns:
        :obj:`gdb.Value`: The converted ``struct device``.  The value is
        of type ``struct device``.
    """

    if struct_has_member(gendisk['part0'], 'bd_device'):
        return gendisk['part0']['bd_device']

    return gendisk['part0']['__dev']

def part_to_dev(part: gdb.Value) -> gdb.Value:
    """
    Converts a ``struct hd_struct`` that embeds a ``struct device`` to
    the ``struct device``.

    Args:
        dev: A ``struct hd_struct`` that embeds a ``struct device``.  The
            value must be of type ``struct device``.

    Returns:
        :obj:`gdb.Value`: The converted ``struct device``.  The value is
        of type ``struct device``.
    """
    return part['__dev']


def for_each_block_device(subtype: gdb.Value = None) -> Iterable[gdb.Value]:
    """
    Iterates over each block device registered with the block class.

    This method iterates over the block_class klist and yields every
    member found.  The members are either struct gendisk or
    struct hd_struct, depending on whether it describes an entire
    disk or a partition, respectively.

    The members can be filtered by providing a subtype, which
    corresponds to a the the type field of the struct device.

    Args:
        subtype (optional): The ``struct device_type`` that will be used
            to match and filter.  Typically the values associated with
            the ``disk_type`` or ``part_type`` :obj:`gdb.Symbol`.

    Yields:
        :obj:`gdb.Value`:  The next block device that matches the subtype.
        The value is of type ``struct gendisk`` or ``struct hd_struct``.

    Raises:
        :obj:`RuntimeError`: An unknown device type was encountered
            during iteration.
        :obj:`TypeError`: The provided subtype was not of
            ``struct device_type`` or ``struct device type *``
    """

    if subtype:
        if get_basic_type(subtype.type) == types.device_type_type:
            subtype = subtype.address
        elif get_basic_type(subtype.type) != types.device_type_type.pointer():
            raise InvalidArgumentError("subtype must be {} not {}"
                                       .format(types.device_type_type.pointer(),
                                               subtype.type.unqualified()))
    for dev in for_each_class_device(symvals.block_class, subtype):
        if dev['type'] == symvals.disk_type.address:
            yield dev_to_gendisk(dev)
        elif dev['type'] == symvals.part_type.address:
            yield dev_to_part(dev)
        else:
            raise RuntimeError("Encountered unexpected device type {}"
                               .format(dev['type']))

def for_each_disk() -> Iterable[gdb.Value]:
    """
    Iterates over each block device registered with the block class
    that corresponds to an entire disk.

    This is an alias for for_each_block_device(``disk_type``)
    """

    return for_each_block_device(symvals.disk_type)

def gendisk_name(gendisk: gdb.Value) -> str:
    """
    Returns the name of the provided block device.

    This method evaluates the block device and returns the name,
    including partition number, if applicable.

    Args:
        gendisk: A ``struct gendisk`` or ``struct hd_struct`` for which to
            return the name.  The value must be of type ``struct gendisk``
            or ``struct hd_struct``.

    Returns:
        :obj:`str`: The name of the block device

    Raises:
        :obj:`.InvalidArgumentError`: gendisk does not describe a
            ``struct gendisk`` or ``struct hd_struct``
    """
    if gendisk.type.code == gdb.TYPE_CODE_PTR:
        gendisk = gendisk.dereference()

    if get_basic_type(gendisk.type) == types.gendisk_type:
        return gendisk['disk_name'].string()

    if get_basic_type(gendisk.type) == types.hd_struct_type:
        parent = dev_to_gendisk(part_to_dev(gendisk)['parent'])
        return "{}{:d}".format(gendisk_name(parent), int(gendisk['partno']))

    raise InvalidArgumentError("expected {} or {}, not {}"
                               .format(types.gendisk_type,
                                       types.hd_struct_type,
                                       gendisk.type.unqualified()))

def block_device_name(bdev: gdb.Value) -> str:
    """
    Returns the name of the provided block device.

    This method evaluates the block device and returns the name,
    including partition number, if applicable.

    Args:
        bdev: A ``struct block_device`` for which to return the name.  The
            value must be of type ``struct block_device``.

    Returns:
        :obj:`str`: The name of the block device
    """
    return gendisk_name(bdev['bd_disk'])


def is_bdev_inode(inode: gdb.Value) -> bool:
    """
    Tests whether the provided ``struct inode`` describes a block device

    This method evaluates the inode and returns :obj:`True` or :obj:`False`,
    depending on whether the inode describes a block device.

    Args:
        bdev: The ``struct inode`` to test whether it describes a block device.
            The value must be of type ``struct inode``.

    Returns:
        :obj:`bool`: :obj:`True` if the inode describes a block device,
        :obj:`False` otherwise.
    """
    return inode['i_sb'] == symvals.blockdev_superblock

def inode_to_block_device(inode: gdb.Value) -> gdb.Value:
    """
    Returns the block device associated with this inode.

    If the inode describes a block device, return that block device.
    Otherwise, raise InvalidArgumentError.

    Args:
        inode: The ``struct inode`` for which to return the associated
            block device.  The value must be of type ``struct inode``.

    Returns:
        :obj:`gdb.Value`: The ``struct block_device`` associated with the
        provided ``struct inode``.  The value is of type
        ``struct block_device``.

    Raises:
        :obj:`.InvalidArgumentError`: inode does not describe a block device
    """
    if inode['i_sb'] != symvals.blockdev_superblock:
        raise InvalidArgumentError("inode does not correspond to block device")
    return container_of(inode, types.bdev_inode_type, 'vfs_inode')['bdev']

def inode_on_bdev(inode: gdb.Value) -> gdb.Value:
    """
    Returns the block device associated with this inode.

    If the inode describes a block device, return that block device.
    Otherwise, return the block device, if any, associated
    with the inode's super block.

    Args:
        inode: The ``struct inode`` for which to return the associated
            block device.  The value must be of type ``struct inode``.

    Returns:
        :obj:`gdb.Value`: The ``struct block_device`` associated with the
        provided ``struct inode``.  The value is of type ``struct inode``.
    """
    if is_bdev_inode(inode):
        return inode_to_block_device(inode)
    return inode['i_sb']['s_bdev'].dereference()

def request_age_ms(request: gdb.Value) -> int:
    """
    Returns the age of the request in milliseconds

    This method returns the difference between the current time
    (``jiffies``) and the request's ``start_time``, in milliseconds.

    Args:
        request: The ``struct request`` used to determine age.  The value
            is of type ``struct request``.

    Returns:
        :obj:`int`: Difference between the request's ``start_time`` and
            current ``jiffies`` in milliseconds.
    """
    return jiffies_to_msec(kernel.jiffies - request['start_time'])

def rq_data_dir(request: gdb.Value) -> int:
    """
    Returns direction of the request

    This method returns 0 if the request is read and 1 if the request is write.

    Args:
        request: The ``struct request`` to query data direction in.

    Returns:
        :obj:`int`: 0 for reads, 1 for writes.
    """
    if request['cmd_flags'] & 1 != 0:
        return WRITE
    return READ

def rq_is_sync(request: gdb.Value) -> bool:
    """
    Returns whether request is synchronous

    This method returns True if the request is synchronous and False otherwise.

    Args:
        request: The ``struct request`` to query.

    Returns:
        :obj:`bool`: True for synchronous requests, False otherwise.
    """
    return (request['cmd_flags'] & 1 == 0 or
            request['cmd_flags'] & (REQ_SYNC | REQ_FUA | REQ_PREFLUSH) != 0)


_rq_in_flight: Callable[[gdb.Value], bool]

def _rq_in_flight_rq_state(request: gdb.Value) -> bool:
    return (request['rq_state'] !=
            types.enum_mq_rq_state_type['MQ_RQ_IDLE'])

def _rq_in_flight_atomic_flags(request: gdb.Value) -> bool:
    return (request['atomic_flags'] &
            (1 << int(types.enum_rq_atomic_flags_type['REQ_ATOM_STARTED'].enumval)) != 0)

def _rq_in_flight_cmd_flags(request: gdb.Value) -> bool:
    return request['cmd_flags'] & REQ_STARTED != 0

def rq_in_flight(request: gdb.Value) -> bool:
    """
    Returns whether request is currently processed by the device

    This method returns True if the request is being processed by the device

    Args:
        request: The ``struct request`` to query.

    Returns:
        :obj:`bool`: True for requests in flight, False otherwise.
    """
    return _rq_in_flight(request)

def queue_is_mq(queue: gdb.Value) -> bool:
    """
    Tests whether the queue is blk-mq queue.

    Args:
        queue: The request queue to test. The value must be
            of type ``struct request_queue``.

    Returns:
        :obj:`bool`: whether the ``struct request_queue`` is a multiqueue queue
    """
    if not struct_has_member(queue, 'mq_ops'):
        return False
    return int(queue['mq_ops']) != 0

# pylint: disable=unused-argument
def _check_types(result: gdb.Symbol) -> None:
    try:
        if symvals.part_type.type.unqualified() != types.device_type_type:
            raise TypeError("part_type expected to be {} not {}"
                            .format(symvals.device_type_type,
                                    types.part_type.type))

        if symvals.disk_type.type.unqualified() != types.device_type_type:
            raise TypeError("disk_type expected to be {} not {}"
                            .format(symvals.device_type_type,
                                    types.disk_type.type))
    except DelayedAttributeError:
        pass

# Export REQ_ flags into namespace as constants
def _export_req_flags(req_flag_bits: gdb.Type) -> None:
    for (name, field) in req_flag_bits.items():
        globals()[name[2:]] = 1 << field.enumval

    # Define to 0 flags that don't exist.
    for name in ['REQ_PREFLUSH', 'REQ_FLUSH']:
        if not name in globals():
            globals()[name] = 0

# Check struct request and define functions based on its current form in this
# kernel
def _check_struct_request(request_s: gdb.Type) -> None:
    if struct_has_member(request_s, 'rq_state'):
        impl = _rq_in_flight_rq_state
    elif struct_has_member(request_s, 'atomic_flags'):
        impl = _rq_in_flight_atomic_flags
    else:
        impl = _rq_in_flight_cmd_flags
    globals()['_rq_in_flight'] = impl

symbol_cbs = SymbolCallbacks([('disk_type', _check_types),
                              ('part_type', _check_types)])
type_cbs = TypeCallbacks([('struct device_type', _check_types),
                          ('enum req_flag_bits', _export_req_flags),
                          ('struct request', _check_struct_request)])
