import logging

import gdb

import libslub.frontend.helpers as helpers
import libslub.slub.sb as sb

log = logging.getLogger("libslub")
log.trace("slab_alloc.py")

# You may have to choose which method works best for your environment
#
# allocate_slab() is the function we are interested to track since it returns the struct page*
# for the newly allocated slab
#
# The following call trace exists:
# __slab_alloc()                  - return address of new_slab() hooked in method 3
#    |- new_slab()                - hooked + finish by method 1
#       |- allocate_slab()        - hooked + finish by method 2


class NewSlabFinish(gdb.FinishBreakpoint):
    """Method 1 to track slab allocations

    See NewSlab()

    NOTE: if gdb crashes when you use this FinishBreakpoint, you may want
    to use the normal Breakpoint in Method 3 below instead
    """

    def __init__(self, sb, name):
        frame = gdb.newest_frame().older()
        super(NewSlabFinish, self).__init__(frame, internal=sb.bps_hidden)
        self.sb = sb
        self.name = name

    def stop(self):
        # self.return_value is only valid for functions with debug symbols
        # enabled... which doesn't seem to work for this function in stock
        # Ubuntu for instance.
        addr = int(self.return_value) & sb.Slub.UNSIGNED_LONG
        self.sb.notify_slab_alloc(self.name, addr)
        return False  # continue execution


class NewSlab(gdb.Breakpoint):
    """Method 1 to track slab allocations"""

    def __init__(self, sb):
        helpers.clear_existing_breakpoints("new_slab")
        super(NewSlab, self).__init__("new_slab", internal=sb.bps_hidden)
        self.sb = sb

        # This register is used to read the slab_cache variable in the event
        # that this symbol is optimized out by the compiler... this is normally
        # the first argument to the function so it should be in rdi, but it may
        # change...
        # XXX - add ARM support
        self.register = "rdi"

    def stop(self):
        slab_cache = gdb.selected_frame().read_var("s")
        if str(slab_cache) == "<optimized out>":
            kmem_cache = gdb.lookup_type("struct kmem_cache")
            # print("Found slab at: 0x%x" % entry)
            slab_cache_addr = gdb.selected_frame().read_register(self.register)
            entry = gdb.Value(slab_cache_addr)
            slab_cache = entry.cast(kmem_cache.pointer())
        name = slab_cache["name"].string()
        if name in self.sb.watch_caches:
            NewSlabFinish(self.sb, name)
        return False  # continue execution


class NewSlabFinish2(gdb.FinishBreakpoint):
    """Method 2 to track slab allocations

    See AllocateSlab()

    NOTE: if gdb crashes when you use this FinishBreakpoint, you may want
    to use the normal Breakpoint in Method 3 below instead
    """

    def __init__(self, sb, name):
        # frame = gdb.newest_frame()
        frame = gdb.newest_frame().older()
        super(NewSlabFinish, self).__init__(frame, internal=sb.bps_hidden)
        self.sb = sb
        self.name = name

    def stop(self):
        print("NewSlabFinish.stop()")
        addr = int(self.return_value) & sb.Slub.UNSIGNED_LONG
        self.sb.notify_slab_alloc(self.name, addr)
        return False  # continue execution


# This function works more reliably on Ubuntu
# XXX - if we assume the gdb session has lx tools we could parse lx-version to
# try to work some of it out....
class AllocateSlab(gdb.Breakpoint):
    """Method 2 to track slab allocations"""

    def __init__(self, sb):
        helpers.clear_existing_breakpoints("allocate_slab")
        super(AllocateSlab, self).__init__("allocate_slab", internal=sb.bps_hidden)
        self.sb = sb

        # This register is used to read the slab_cache variable in the event
        # that this symbol is optimized out by the compiler... this is normally
        # the first argument to the function so it should be in rdi, but it may
        # change...
        # XXX - add ARM support
        self.register = "rdi"

    def stop(self):
        slab_cache = gdb.selected_frame().read_var("s")
        if str(slab_cache) == "<optimized out>":
            kmem_cache = gdb.lookup_type("struct kmem_cache")
            # print("Found slab at: 0x%x" % entry)
            slab_cache_addr = gdb.selected_frame().read_register(self.register)
            entry = gdb.Value(slab_cache_addr)
            slab_cache = entry.cast(kmem_cache.pointer())
        name = slab_cache["name"].string()
        if name in self.sb.watch_caches:
            NewSlabFinish(self.sb, name)
        return False  # continue execution


class AllocateSlabReturned(gdb.Breakpoint):
    """Method 3 to track slab allocations"""

    def __init__(self, sb, bp_address):
        log.debug("AllocateSlabReturned.__init__()")
        helpers.clear_existing_breakpoints(bp_address)
        super(AllocateSlabReturned, self).__init__(bp_address, internal=sb.bps_hidden)
        self.sb = sb

    def stop(self):
        log.debug("AllocateSlabReturned.stop()")
        slab_cache = gdb.selected_frame().read_var("s")
        name = slab_cache["name"].string()
        addr = gdb.selected_frame().read_var("page")
        addr = int(addr) & sb.Slub.UNSIGNED_LONG
        self.sb.notify_slab_alloc(name, addr)
        return False  # continue execution
