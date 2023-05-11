import argparse
import struct
import sys
import traceback
import gdb
import shlex
import importlib
import logging
from functools import wraps, lru_cache

import libslub.frontend.helpers2 as h2
importlib.reload(h2)
import libslub.slub.sb as sb
importlib.reload(sb)

log = logging.getLogger("libslub")
log.trace(f"slab_free.py")

class DiscardSlab(gdb.Breakpoint):
    """Track slab destructions/frees
    """
    def __init__(self, sb):
        h2.clear_existing_breakpoints("discard_slab")
        super(DiscardSlab, self).__init__("discard_slab", internal=sb.bps_hidden)
        self.sb = sb

    def stop(self):
        slab_cache = gdb.selected_frame().read_var("s")
        name = slab_cache["name"].string()
        page = gdb.selected_frame().read_var("page")
        addr = int(page) & sb.sb.UNSIGNED_LONG
        self.sb.notify_slab_free(name, addr)
        return False # continue execution