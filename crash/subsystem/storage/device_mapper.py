# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import gdb
import sys

if sys.version_info.major >= 3:
    long = int

from crash.infra import CrashBaseClass
from crash.subsystem.storage import Storage as block

class DeviceMapper(CrashBaseClass):
    __types__ = [ 'struct dm_rq_clone_bio_info *',
                  'struct dm_target_io *' ]
    __symbol_callbacks__ = [
                ('end_clone_bio', 'register_end_clone_bio'),
                ('clone_endio', 'register_clone_endio') ]

    @classmethod
    def register_end_clone_bio(cls, sym):
        block.register_bio_decoder(sym, cls.decode_clone_bio_rq)

    @classmethod
    def register_clone_endio(cls, sym):
        block.register_bio_decoder(sym, cls.decode_clone_bio)

    @classmethod
    def decode_clone_bio_rq(cls, bio):
        info = bio['bi_private'].cast(cls.dm_rq_clone_bio_info_p_type)
        count = bio['bi_cnt']['counter']

        # We can pull the related bios together here if required
        # b = bio['bi_next']
        # while long(b) != 0:
        #    b = b['bi_next']

        bio = info['orig']

        chain = {
            'bio' : bio,
            'description' : 'Request-based Device Mapper',
        }

        return chain

    @classmethod
    def decode_clone_bio(cls, bio):
        tio = bio['bi_private'].cast(dm_target_io_p_type)

        chain = {
            'bio' : tio['io']['bio'],
            'description' : 'Bio-based Device Mapper'
        }

        return chain
