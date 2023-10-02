import logging

import gdb

import libslub.frontend.helpers as helpers
import libslub.slub.sb as sb

log = logging.getLogger("libslub")
log.trace("slab_free.py")


class DiscardSlab(gdb.Breakpoint):
    """Track slab destructions/frees"""

    def __init__(self, sb):
        helpers.clear_existing_breakpoints("discard_slab")
        super(DiscardSlab, self).__init__("discard_slab", internal=sb.bps_hidden)
        self.sb = sb

    def stop(self):
        slab_cache = gdb.selected_frame().read_var("s")
        name = slab_cache["name"].string()
        page = gdb.selected_frame().read_var("page")
        addr = int(page) & sb.Slub.UNSIGNED_LONG
        self.sb.notify_slab_free(name, addr)
        return False  # continue execution
