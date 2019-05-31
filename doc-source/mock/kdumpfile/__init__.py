# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import addrxlat

class attrdict(object):
    def __init__(self):
        self.dict = dict()

    def __setitem__(self, name, value):
        self.dict[name] = value

    def __getitem__(self, name):
        return self.dict[name]

    def __setattr__(self, name, value):
        self.dict[name] = value

    def __getattr__(self, name):
        return self.dict[name]

    def get(self, name, default):
        return self.dict[name]

class kdumpfile(object):
    def __init__(self, file):
        self.attr = attrdict()
        self.attr.cpu = attrdict()

    def read(self, mode, offset, length):
        return buffer()

    def get_addrxlat_ctx(self):
        return addrxlat.Context()

    def get_addrxlat_sys(self):
        return addrxlat.System()

KDUMP_KVADDR = 0
