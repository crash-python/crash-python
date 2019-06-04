#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, Any

from crash.cache import CrashCache

class CrashCacheSlab(CrashCache):

    def __init__(self) -> None:
        super().__init__()
        self.refresh()

    def refresh(self) -> None:
        self.populated = False
        self.kmem_caches: Dict[str, Any] = dict()
        self.kmem_caches_by_addr: Dict[int, Any] = dict()

cache = CrashCacheSlab()
