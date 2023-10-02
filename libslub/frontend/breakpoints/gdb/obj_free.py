import logging

import gdb

import libslub.frontend.helpers as helpers
import libslub.slub.sb as sb

log = logging.getLogger("libslub")
log.trace("obj_free.py")


class KmemCacheFreeFinish(gdb.FinishBreakpoint):
    """Method 1 to track object frees on a given slab associated with a slab cache

    See KmemCacheFree()

    NOTE: if gdb crashes when you use this FinishBreakpoint, you may want
    to use the normal Breakpoint in Method 2 below instead
    """

    def __init__(self, sb, name, addr):
        frame = gdb.newest_frame().older()
        super(KmemCacheFreeFinish, self).__init__(frame, internal=sb.bps_hidden)
        self.sb = sb
        self.name = name
        self.addr = addr

    def stop(self):
        self.sb.notify_obj_free(self.name, self.addr)
        if self.name in self.sb.break_caches:
            return True
        return False  # continue execution


class KmemCacheFree(gdb.Breakpoint):
    """Method 1 to track object frees on a given slab associated with a slab cache

    An invisible breakpoint for intercepting kmem_cache_free calls
    """

    def __init__(self, sb):
        helpers.clear_existing_breakpoints("kmem_cache_free")
        super(KmemCacheFree, self).__init__("kmem_cache_free", internal=sb.bps_hidden)
        self.sb = sb

    def stop(self):
        slab_cache = gdb.selected_frame().read_var("s")
        name = slab_cache["name"].string()
        x = gdb.selected_frame().read_var("x")
        addr = int(x) & sb.Slub.UNSIGNED_LONG
        if name in self.sb.trace_caches or name in self.sb.break_caches:
            KmemCacheFreeFinish(self.sb, name, addr)


class KmemCacheFreeReturned(gdb.Breakpoint):
    """Method 2 to track object frees on a given slab associated with a slab cache"""

    def __init__(self, sb, bp_address):
        helpers.clear_existing_breakpoints(bp_address)
        super(KmemCacheFreeReturned, self).__init__(bp_address, internal=sb.bps_hidden)
        self.sb = sb

    def stop(self):
        slab_cache = gdb.selected_frame().read_var("s")
        name = slab_cache["name"].string()
        x = gdb.selected_frame().read_var("x")
        addr = int(x) & sb.Slub.UNSIGNED_LONG
        self.sb.notify_obj_free(name, addr)
        if name in self.sb.break_caches:
            return True
        return False  # continue execution
