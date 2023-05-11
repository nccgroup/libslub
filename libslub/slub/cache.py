import struct
import sys
import logging
import importlib
import time

import libslub.slub.kmem_cache as kc
importlib.reload(kc)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.frontend.helpers as h
importlib.reload(h)

log = logging.getLogger("libslub")
log.trace("cache.py")

class cache:
    """Hold cached information such as our own classes representing slab structures, 
    as well as objects/chunk's addresses in the respective freelists.

    Since browsing all these big structures and arrays can be slow in gdb, we cache
    them in this class."""

    def __init__(self, sb):
        self.sb = sb

        # each key is a slab cache name (e.g. "kmalloc-1k")
        # each value is a kmem_cache class holding all the useful information
        self.slab_caches = {}

    def update_kmem_cache(self, name=None, show_status=False, use_cache=False):
        """Update the kmem_cache object
        
        :param name: slab cache name (e.g. "kmalloc-1k")
        """

        log.debug("cache.update_kmem_cache()")

        # nothing to update if we use the cache
        if use_cache:
            return

        if name is None:
            slab_caches = sb.sb.iter_slab_caches()
            print("Fetching all slab caches, this will take a while... (use -n to specify a slab cache)")
        else:
            slab_cache = sb.sb.find_slab_cache(name)
            if slab_cache is None:
                print("Slab cache '%s' not found" % name)
                return
            slab_caches = [slab_cache]

        start_time = time.time()
        for slab_cache in slab_caches:
            kmem_cache = kc.kmem_cache(self.sb, value=slab_cache)
            if show_status:
                print(f"Caching slab cache: {kmem_cache.name}")
            self.slab_caches[kmem_cache.name] = kmem_cache
        end_time = time.time()
        if name is None:
            print("Fetched in %s" % h.hms_string(end_time-start_time))
    
    def update_all(self, name=None, show_status=False, use_cache=False):
        self.update_kmem_cache(name=name, show_status=show_status, use_cache=use_cache)
