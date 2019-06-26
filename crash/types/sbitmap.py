#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
The crash.types.sbitmap module provides helpers for iterating and scanning
scalable bitmaps

"""

from typing import Iterable

from crash.exceptions import InvalidArgumentError
from crash.util.symbols import Types
from crash.util import struct_has_member

import gdb

types = Types(['struct sbitmap', 'struct sbitmap_word'])

def sbitmap_for_each_set(sbitmap: gdb.Value) -> Iterable[int]:
    """
    Yield each set bit in a scalable bitmap

    Args:
        sbitmap: The bitmap to iterate.

    Yields:
        :obj:`int`: The position of a bit that is set

    """

    length = int(sbitmap['depth'])
    for i in range(0, int(sbitmap['map_nr'])):
        word = sbitmap['map'][i]['word']
        if struct_has_member(sbitmap['map'][i], 'cleared'):
            word &= ~sbitmap['map'][i]['cleared']
        offset = i << int(sbitmap['shift'])
        bits = min(int(sbitmap['map'][i]['depth']), length - offset)
        for j in range(0, bits):
            if word & (1 << j):
                yield offset + j

