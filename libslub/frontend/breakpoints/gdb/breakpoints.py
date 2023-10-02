import logging

import libslub.frontend.breakpoints.gdb.obj_alloc as obj_alloc
import libslub.frontend.breakpoints.gdb.obj_free as obj_free
import libslub.frontend.breakpoints.gdb.slab_alloc as slab_alloc
import libslub.frontend.breakpoints.gdb.slab_free as slab_free

log = logging.getLogger("libslub")
log.trace("breakpoints.py")

# We dump the version from the kernel and try to find if we have breakpoints,
# otherwise we don't enable them.
# NOTE: Make sure that you update debugger.get_kernel_version() to return the
# right kernel. If it's not ubuntu, you probably also have to hack breakpoint
# class initialization in sb.py
breakpoint_table = {
    "Ubuntu 5.15.0-27.28-generic": {
        "kmem_cache_free_returned": "mm/slub.c:3509",
        # void *kmem_cache_alloc(struct kmem_cache *s, gfp_t gfpflags)
        # {
        # 	void *ret = slab_alloc(s, gfpflags, _RET_IP_, s->object_size);
        #
        # 	trace_kmem_cache_alloc(_RET_IP_, ret, s->object_size,           // breakpoint here
        # 				s->size, gfpflags);
        #
        # 	return ret;
        # }
        "kmem_cache_alloc_returned": "mm/slub.c:3228",
        # XXX - I am using this technique because the original seems to be broken, in
        # so far as the finish breakpoint never hits from inside python.
        # If you need to change this, find "new_slab_objects()" or "___slab_alloc()"
        # and look for the location where there is an assignment `page = new_slab()`. Ex:
        # ```
        # static inline void *new_slab_objects(struct kmem_cache *s, gfp_t flags,
        # int node, struct kmem_cache_cpu **pc)
        # {
        # void *freelist;
        # struct kmem_cache_cpu *c = *pc;
        # struct page *page;
        #
        # WARN_ON_ONCE(s->ctor && (flags & __GFP_ZERO));
        #
        # freelist = get_partial(s, flags, node, c);
        #
        # if (freelist)
        # return freelist;
        #
        # page = new_slab(s, flags, node);
        # if (page) {                                           // breakpoint here
        # ```
        "allocate_slab_returned": "mm/slub.c:3002",
    },
}


class breakpoints:
    def __init__(self, sb, kernel_version):
        """
        Holds all the breakpoints that are useful to trace/log SLUB allocator internal behaviours
        such as when a new slab is created or when objects are allocated on a given slab
        """
        log.debug("breakpoints.__init__()")

        self.supported = False
        self.sb = sb

        if not kernel_version or kernel_version not in breakpoint_table.keys():
            print(
                f"WARNING: breakpoints are not supported for kernel version '{kernel_version}'"
            )
            return
        self.supported = True
        # XXX - Some breakpoints do not work well in some environments
        # or crash gdb so enable the ones that work for you :)
        bps_locations = breakpoint_table[kernel_version]

        # self.obj_alloc_bp = obj_alloc.KmemCacheAlloc(self.sb)
        self.obj_alloc_bp = obj_alloc.KmemCacheAllocReturned(
            self.sb, bps_locations["kmem_cache_alloc_returned"]
        )

        # self.obj_free_bp = obj_free.KmemCacheFree(self.sb)
        self.obj_free_bp = obj_free.KmemCacheFreeReturned(
            self.sb, bps_locations["kmem_cache_free_returned"]
        )

        # self.slab_alloc_bp = slab_alloc.NewSlab(self)
        # self.slab_alloc_bp = slab_alloc.AllocateSlab(self.sb)
        self.slab_alloc_bp = slab_alloc.AllocateSlabReturned(
            self.sb, bps_locations["allocate_slab_returned"]
        )

        self.slab_free_bp = slab_free.DiscardSlab(self.sb)

        self.update_breakpoints()

    def update_breakpoints(self):
        if not self.supported:
            return
        enabled = bool(self.sb.trace_caches) or bool(self.sb.break_caches)
        self.obj_alloc_bp.enabled = enabled
        self.obj_free_bp.enabled = enabled

        enabled = bool(self.sb.watch_caches)
        self.slab_alloc_bp.enabled = enabled
        self.slab_free_bp.enabled = enabled
