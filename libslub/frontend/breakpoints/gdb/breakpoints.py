import argparse
import struct
import sys
import traceback
import gdb
import shlex
import importlib
import logging
from functools import wraps, lru_cache

import libslub.frontend.helpers as h
importlib.reload(h)
import libslub.frontend.helpers2 as h2
importlib.reload(h2)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.frontend.breakpoints.gdb.slab_alloc as slab_alloc
importlib.reload(slab_alloc)
import libslub.frontend.breakpoints.gdb.slab_free as slab_free
importlib.reload(slab_free)
import libslub.frontend.breakpoints.gdb.obj_alloc as obj_alloc
importlib.reload(obj_alloc)
import libslub.frontend.breakpoints.gdb.obj_free as obj_free
importlib.reload(obj_free)

log = logging.getLogger("libslub")
log.trace("breakpoints.py")

class breakpoints:

    def __init__(self, sb):
        """
        Holds all the breakpoints that are useful to trace/log SLUB allocator internal behaviours
        such as when a new slab is created or when objects are allocated on a given slab
        """
        log.debug("breakpoints.__init__()")

        self.sb = sb

        # XXX - Some breakpoints do not work well in some environments
        # or crash gdb so enable the ones that work for you :)

        #self.obj_alloc_bp = obj_alloc.KmemCacheAlloc(self.sb)
        self.obj_alloc_bp = obj_alloc.KmemCacheAllocReturned(self.sb)
        
        #self.obj_free_bp = obj_free.KmemCacheFree(self.sb)
        self.obj_free_bp = obj_free.KmemCacheFreeReturned(self.sb)
        
        #self.slab_alloc_bp = slab_alloc.NewSlab(self)
        #self.slab_alloc_bp = slab_alloc.AllocateSlab(self.sb)
        self.slab_alloc_bp = slab_alloc.AllocateSlabReturned(self.sb)
        
        self.slab_free_bp = slab_free.DiscardSlab(self.sb)

        self.update_breakpoints()

    def update_breakpoints(self):
        enabled = bool(self.sb.trace_caches) or bool(self.sb.break_caches)
        self.obj_alloc_bp.enabled = enabled
        self.obj_free_bp.enabled = enabled

        enabled = bool(self.sb.watch_caches)
        self.slab_alloc_bp.enabled = enabled
        self.slab_free_bp.enabled = enabled