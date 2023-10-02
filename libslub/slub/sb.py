import logging
from enum import Enum

import gdb

import libslub.commands.db as cmd_db
import libslub.frontend.breakpoints.gdb.breakpoints as breakpoints
import libslub.frontend.helpers as h
import libslub.slub.cache as c

log = logging.getLogger("libslub")
log.trace("sb.py")


class SlabType(Enum):
    MAIN_SLAB = 0
    PARTIAL_SLAB = 1
    NODE_SLAB = 2  # partial slab in node
    FULL_SLAB = 3  # full slab in node


# XXX - some methods in this helper class could be changed to fetch information from the cache instead of fetching it from
# memory again
class Slub:
    UNSIGNED_INT = 0xFFFFFFFF
    UNSIGNED_LONG = 0xFFFFFFFFFFFFFFFF
    TYPE_CODE_HAS_FIELDS = [gdb.TYPE_CODE_STRUCT, gdb.TYPE_CODE_UNION]

    # XXX - move to sblist.py?
    kmalloc_caches = [
        "kmalloc-%s" % n
        for n in [
            "8",
            "16",
            "32",
            "64",
            "96",
            "128",
            "192",
            "256",
            "512",
            "1k",
            "2k",
            "4k",
            "8k",
        ]
    ]

    FLAGS = {
        0x00000100: "SLAB_DEBUG_FREE",
        0x00000400: "SLAB_RED_ZONE",
        0x00000800: "SLAB_POISON",
        0x00002000: "SLAB_HWCACHE_ALIGN",
        0x00004000: "SLAB_CACHE_DMA",
        0x00008000: "SLAB_CACHE_DMA32",
        0x00010000: "SLAB_STORE_USER",
        0x00020000: "SLAB_RECLAIM_ACCOUNT",
        0x00040000: "SLAB_PANIC",
        0x00080000: "SLAB_DESTROY_BY_RCU",
        0x00100000: "SLAB_MEM_SPREAD",
        0x00200000: "SLAB_TRACE",
        0x00400000: "SLAB_DEBUG_OBJECTS",
        0x00800000: "SLAB_NOLEAKTRACE",
        0x01000000: "SLAB_NOTRACK",
        0x02000000: "SLAB_FAILSLAB",
        0x04000000: "SLAB_ACCOUNT",
        0x08000000: "SLAB_KASAN",
        0x10000000: "SLAB_DEACTIVATED",
        # 0x40000000: "__CMPXCHG_DOUBLE",
        # 0x80000000: "__OBJECT_POISON",
    }

    def __init__(self, debugger=None, breakpoints_enabled=False):
        """
        :param debugger: the pydbg object

        Internally, everything is kept as gdb.Value
        """

        self.dbg = debugger
        self.breakpoints_enabled = breakpoints_enabled
        self.node_num = self._get_node_num()  # number of NUMA node
        self.arch = self.dbg.get_arch_name()
        self._check_slub()

        self.cpu_num = gdb.lookup_global_symbol("nr_cpu_ids").value()
        self.per_cpu_offset = gdb.lookup_global_symbol("__per_cpu_offset").value()
        try:
            self.memstart_addr = gdb.lookup_global_symbol("memstart_addr").value()
        except Exception:
            self.memstart_addr = None

        # Defines if the breakpoints used for tracking should be hidden to the user
        # as used for "internal" in https://sourceware.org/gdb/onlinedocs/gdb/Breakpoints-In-Python.html
        self.bps_hidden = True  # set to False for debugging only

        # List of cache names (e.g. "kmalloc-1k") to track object allocations/frees
        # for logging purpose or for breaking in the debugger
        self.trace_caches = []
        self.break_caches = []
        # List of cache names (e.g. "kmalloc-1k") to track slab allocations/frees so
        # we can list the full-slabs contents since they are not tracked by SLUB
        self.watch_caches = []
        # List of slab addresses (struct page*) for previously allocated slabs that we
        # managed to track. This is so we can list the full-slabs contents when needed
        self.slabs_list = []
        if self.breakpoints_enabled:
            # We have to make sure we have supported versions, so grab the
            # version...
            kversion = self.dbg.get_kernel_version()
            # HACK: At the moment we just pull out on an ubuntu version, and try
            # to correlate it. We try to pull it out the end of the string like this:
            # Linux version 5.15.0-27-generic (buildd@ubuntu) ... (Ubuntu 5.15.0-27.28-generic 5.15.30)
            if "Ubuntu" in kversion and kversion.endswith(")"):
                kversion = " ".join(kversion.split("(")[-1].split()[0:2])
                self.breakpoints = breakpoints.breakpoints(self, kversion)
            else:
                self.breakpoints = None

        self.cache = c.cache(self)

    def _get_node_num(self):
        """
        get the number of NUMA nodes in the hardware
        reference:
        https://futurewei-cloud.github.io/ARM-Datacenter/qemu/how-to-configure-qemu-numa-nodes/
        https://elixir.bootlin.com/linux/v4.15/source/include/linux/nodemask.h#L433
        """

        # TODO: This can't be gdb-specific
        node_states = gdb.lookup_global_symbol("node_states").value()
        node_mask = node_states[1]["bits"][0]  # 1 means N_ONLINE
        return bin(node_mask).count("1")

    def _check_slub(self):
        """
        make sure the target kernel is compiled with SLUB, not SLAB or SLOB
        """
        allocator = "SLOB"
        kmem_cache = gdb.lookup_type("struct kmem_cache")
        for field in gdb.types.deep_items(kmem_cache):
            name = field[0]
            if name == "batchcount":
                allocator = "SLAB"
                break
            elif name == "inuse":
                allocator = "SLUB"
                break
        if allocator != "SLUB":
            raise ValueError("slabdbg does not support allocator: %s" % allocator)

    @staticmethod
    def get_field_bitpos(type, member):
        """XXX"""

        for field in type.fields():
            if field.name == member:
                return field.bitpos
            if field.type.code in Slub.TYPE_CODE_HAS_FIELDS:
                bitpos = Slub.get_field_bitpos(field.type, member)
                if bitpos is not None:
                    return field.bitpos + bitpos
        return None

    @staticmethod
    def for_each_entry(type, head, member):
        """Iterator for a linked list pointed by head (i.e. starting address) where each element
        of the linked list is of the "type" type and the next element being found at the "member"
        member of the "type" type.

        @param type: a gdb.Type (e.g. representing "struct kmem_cache") to cast elements in the linked list pointed by head
        @param head: a gdb.Value for a "struct list_head" (linked list) represented by a dictionary (so having the "next" and "prev" keys)
        @param member: the name of the linked list pointed by head in the provided type
                       e.g. "struct kmem_cache" has its linked list named "list"

        @return: iterator returning the gdb.Type casted objects found at the different elements
                 in the linked list pointed by head
        """

        # TODO: Needs to be abstracted away from gdb
        void_p = gdb.lookup_type("void").pointer()  # type represents a void*
        offset = Slub.get_field_bitpos(type, member) // 8

        pos = head["next"].dereference()
        while pos.address != head.address:
            entry = gdb.Value(pos.address.cast(void_p) - offset)
            # print(entry)
            # print(entry.cast(type.pointer()).dereference())
            # print("Found list entry: 0x%x" % entry)
            # Cast the gdb.Value address to the right type and return that as a dictionary
            yield entry.cast(type.pointer()).dereference()
            pos = pos["next"].dereference()

    @staticmethod
    def iter_slab_caches():
        """Iterator for the "struct list_head slab_caches" which is a linked list of "struct kmem_cache*"
        representing all the slab caches on the system.

        struct kmem_cache* kmem_cache: https://elixir.bootlin.com/linux/v5.15/source/mm/slab_common.c#L38

        @return: iterator returning the the different "struct kmem_cache" elements (represented as dictionaries)
                 part of the "list" linked list of the "struct kmem_cache" structure, which head starts
                 at the "slab_caches" global.
        """

        # The "kmem_cache" type as a dictionary
        # struct kmem_cache {: https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L90
        # lookup_type(), see https://sourceware.org/gdb/onlinedocs/gdb/Types-In-Python.html
        kmem_cache_type = gdb.lookup_type("struct kmem_cache")

        # The head of the list for all slab caches on the system (e.g. "kmalloc-64", etc.)
        # https://elixir.bootlin.com/linux/v5.15/source/mm/slab.h#L72
        # lookup_global_symbol(), see https://sourceware.org/gdb/onlinedocs/gdb/Symbols-In-Python.html
        slab_caches = gdb.lookup_global_symbol("slab_caches").value()

        return Slub.for_each_entry(kmem_cache_type, slab_caches, "list")

    @staticmethod
    def find_slab_cache(name):
        for slab_cache in Slub.iter_slab_caches():
            if slab_cache["name"].string() == name:
                return slab_cache
        return None

    @staticmethod
    def get_cache_names():
        for slab_cache in Slub.iter_slab_caches():
            yield slab_cache["name"].string()

    @staticmethod
    def get_flags_list(flags):
        return [Slub.FLAGS[x] for x in Slub.FLAGS if flags & x == x]

    @staticmethod
    def freelist_ptr(slab_cache, freelist, freelist_addr):
        """Return a possibly decoded freelist value

        This function only actually does anything if the random member is found
        in the slab_cache, otherwise we assume that freelist coding isn't
        supported

        Note: At some point in additional bit diffusion technique was added,
        which changes the way there encoding is done... we need a way to test
        for this probably. apossibly decoding it twice and seeing which one is
        a valid address? See XXX below..

        https://patchwork.kernel.org/project/linux-mm/patch/202003051623.AF4F8CB@keescook/

        Newer versions of the linux kernel encode this pointer

        See freelist_ptr in slub.c for implementation:

        static inline void *freelist_ptr(const struct kmem_cache *s, void *ptr,
                         unsigned long ptr_addr)
        {
        #ifdef CONFIG_SLAB_FREELIST_HARDENED
            /*
            return (void *)((unsigned long)ptr ^ s->random ^
                    swab((unsigned long)kasan_reset_tag((void *)ptr_addr)));
        #else
            return ptr;
        #endif
        }

        ptr_addr is the address of the ptr in the kmem_cache structure itself.
        """

        # Not sure how to check for keys in gdb.Value struct... so try instead
        try:
            random = int(slab_cache["random"])
        except Exception:
            return freelist

        # print("Freelist address: 0x%x" % freelist_addr)
        random = int(slab_cache["random"])
        decoded = (
            random
            ^ int(freelist.cast(gdb.lookup_type("unsigned long")))
            ^ h.swap64(freelist_addr)
        )
        # XXX To solve the swap64() possibly not existing, we could check if
        # the decoded address lives inside the slab cache page, since all of
        # the objects should be inside of it...
        return decoded

    @staticmethod
    def walk_linear_memory_region(slab_cache, slab, region_start):
        """Iterator returns each object/chunk address in the slab memory region

        @param slab_cache: slab cache (gdb.Value) associated with a given slab. The reason we pas it is because it contains
               fields to know the size of objects, etc.
        @param slab: slab (gdb.Value) we want to get the objects/chunks from its memory region
        @param region_start: start address of the memory region holding the objects/chunks for that slab
        @return: iterator returns each object/chunk address in the slab memory region
        """

        objects = int(slab["objects"]) & Slub.UNSIGNED_INT
        size = int(slab_cache["size"])

        for address in range(region_start, region_start + objects * size, size):
            yield address

    @staticmethod
    def walk_freelist(slab_cache, freelist):
        """Iterator return each object address in the slab's free list

        @param slab_cache: slab cache associated with a given slab. The reason we pas it is because it contains
                offsets and random values used to find the next element in the freelist
        @param freelist: address of the head of the freelist
        @return: iterator returns each object address in the slab's free list
        """

        void = gdb.lookup_type("void").pointer().pointer()
        offset = int(slab_cache["offset"])

        # Stop when we encounter a NULL pointer
        while freelist:
            address = int(freelist) & Slub.UNSIGNED_LONG
            yield address
            freelist = gdb.Value(address + offset).cast(void).dereference()
            freelist = Slub.freelist_ptr(slab_cache, freelist, address + offset)

    # XXX - move to class: kmem_cache_cpu
    def get_current_slab_cache_cpu(self, slab_cache):
        """
        See https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L91

        @return a gdb.Value representing the current kmem_cache_cpu for that slab cache
        i.e. representing kmem_cache->cpu_slab

        NOTE: The gdb.Value represents a structure and is a simple dictionary
        see https://sourceware.org/gdb/onlinedocs/gdb/Values-From-Inferior.html
        """

        void_p = gdb.lookup_type("void").pointer()  # type represents a void*
        kmem_cache_cpu = gdb.lookup_type(
            "struct kmem_cache_cpu"
        ).pointer()  # type represents a kmem_cache_cpu*

        # selected_thread(), see: https://sourceware.org/gdb/onlinedocs/gdb/Threads-In-Python.html
        current_cpu = gdb.selected_thread().num - 1

        cpu_offset = self.per_cpu_offset[current_cpu]
        cpu_slab = gdb.Value(slab_cache["cpu_slab"].cast(void_p) + cpu_offset)
        return cpu_slab.cast(kmem_cache_cpu).dereference()

    # XXX - move to class: kmem_cache_cpu
    def get_all_slab_cache_cpus(self, slab_cache):
        """
        See https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L91

        @return a list of all the gdb.Value representing all the kmem_cache_cpu for that slab cache
        i.e. representing the different kmem_cache->cpu_slab

        NOTE: The gdb.Value represents a structure and is a simple dictionary
        see https://sourceware.org/gdb/onlinedocs/gdb/Values-From-Inferior.html
        """

        void_p = gdb.lookup_type("void").pointer()  # type represents a void*
        kmem_cache_cpu = gdb.lookup_type(
            "struct kmem_cache_cpu"
        ).pointer()  # type represents a kmem_cache_cpu*

        offset = slab_cache["cpu_slab"]
        result = []
        for cpu_idx in range(self.cpu_num):
            cpu_offset = self.per_cpu_offset[cpu_idx]
            cpu_slab = gdb.Value(offset.cast(void_p) + cpu_offset)
            cpu_slab = cpu_slab.cast(kmem_cache_cpu).dereference()
            result.append(cpu_slab)
        return result

    def notify_obj_alloc(self, name, addr):
        """Called when a breakpoint tracking objects allocations in a given slab hits"""
        if name in self.trace_caches:
            print("Object 0x%x allocated in %s" % (addr, name))

    def notify_obj_free(self, name, addr):
        """Called when a breakpoint tracking objects frees in a given slab hits"""
        if name in self.trace_caches:
            print("Object 0x%x freed in %s" % (addr, name))

    def notify_slab_alloc(self, name, addr):
        """Called when a breakpoint tracking slabs allocations hits"""
        if name in self.watch_caches:
            print("Slab 0x%x allocated in %s" % (addr, name))
            self.slabs_list.append(addr)

    def notify_slab_free(self, name, addr):
        """Called when a breakpoint tracking slabs frees hits"""
        if name in self.watch_caches:
            if addr in self.slabs_list:
                print("Slab 0x%x freed in %s" % (addr, name))
                self.slabs_list.remove(addr)

    # XXX - move to the actual slab object that matches the structure
    def get_full_slabs(self, slab_cache_name):
        """Yield all tracked slab allocations that are determined to be full
        for a given slab cache

        @slab_cache_name: the slab cache name we want the full slabs of (e.g. "kmalloc-1k")
        @return: Yield all the gdb.Value for the slab caches that are full (i.e. dictionaries
                 representing the "struct page*" type)
        """

        # We rely on breakpoints to keep track of allocations/frees of slabs,
        # and keep them inside of slabs_list. This lets us view full slabs that
        # would otherwise not be accessible.
        if slab_cache_name in self.watch_caches:
            yield from Slub.full_slab_from_list(self.slabs_list, slab_cache_name)

        # Alternatively, we rely on the sbslabdb command being used by us to track certain slabs
        # associated with certain chunks address we want to track the slabs of
        if slab_cache_name in cmd_db.slab_db.keys():
            yield from Slub.full_slab_from_list(
                cmd_db.slab_db[slab_cache_name].keys(), slab_cache_name
            )

    @staticmethod
    def full_slab_from_list(slabs_list, slab_cache_name):
        """Yield all tracked slab allocations that are determined to be full
        for a given slab cache

        @slabs_list: the list of struct page* addresses for certain slabs we tracked previously
        @slab_cache_name: the slab cache name we want the full slabs of (e.g. "kmalloc-1k")
        @return: Yield all the gdb.Value for the slab caches that are full (i.e. dictionaries
                 representing the "struct page*" type)

        We make sure that each slab in the
        list is not on the free list (implying non-full), is not frozen
        (implying it's not associated with this specific CPU at the moment?),
        and the name matches whatever cache we are interested in
        """
        page_type = gdb.lookup_type("struct page").pointer()
        for addr in slabs_list:
            slab = gdb.Value(addr).cast(page_type)
            slab_cache = slab["slab_cache"]
            if (
                int(slab_cache) != 0x0
                and slab_cache["name"].string() == slab_cache_name
                and int(slab["frozen"]) == 0
                and not slab["freelist"]
            ):
                yield slab.dereference()

    def page_addr(self, page):
        return self.dbg.get_page_address(page)

    def get_slabs(self, slab_cache):
        """Collect a full list of all the slabs associated with a slab cache"""

        pages = []  # these are actual "struct page*" (gdb.Value) representing a slab

        cpu_cache_list = self.get_all_slab_cache_cpus(slab_cache)

        for cpu_id, cpu_cache in enumerate(cpu_cache_list):
            if cpu_cache["page"]:
                slab = cpu_cache["page"].dereference()
                pages.append(slab)

            if cpu_cache["partial"]:
                slab_ptr = cpu_cache["partial"]
                while slab_ptr:
                    slab = slab_ptr.dereference()
                    pages.append(slab)
                    slab_ptr = slab["next"]

        for node_id in range(self.node_num):
            node_cache = slab_cache["node"][node_id]
            page = gdb.lookup_type("struct page")
            partials = list(self.for_each_entry(page, node_cache["partial"], "lru"))
            if partials:
                for slab in partials:
                    pages.append(slab)

        fulls = list(self.get_full_slabs(slab_cache))
        if fulls:
            for slab in fulls:
                pages.append(slab)

        return pages

    def get_slab_cache_memory_pages(self, slab_cache):
        """Collect a full list of all memory pages holding chunks associated with a slab cache

        Similar to get_slab_cache_memory_pages_ranges() but returning start addresses"""

        pages = self.get_slabs(
            slab_cache
        )  # these are actual "struct page*" (gdb.Value) representing a slab
        page_addrs = []  # these are memory pages ranges holding chunks

        for page in pages:
            address = int(page.address) & Slub.UNSIGNED_LONG
            page_addrs.append(self.page_addr(address))

        return page_addrs

    def get_slab_cache_memory_pages_ranges(self, name=None, dict_enabled=False):
        """Collect a full list of all memory pages ranges holding chunks associated with one or several slab caches

        @param name: slab cache name if known (optional)

        Similar to get_slab_cache_memory_pages() but returning ranges"""

        if dict_enabled is True:
            page_addrs = (
                {}
            )  # key = page* address, and value = array for memory pages ranges holding chunks
        else:
            page_addrs = []  # these are memory pages ranges holding chunks

        if not name:
            slab_caches = Slub.iter_slab_caches()
        else:
            slab_cache = Slub.find_slab_cache(name)
            if slab_cache is None:
                print("Slab cache '%s' not found" % name)
                return None
            slab_caches = [slab_cache]

        for slab_cache in slab_caches:
            pages = self.get_slabs(
                slab_cache
            )  # these are actual "struct page*" (gdb.Value) representing a slab

            for page in pages:
                objects = int(page["objects"]) & Slub.UNSIGNED_INT
                size = int(slab_cache["size"])
                address = int(page.address) & Slub.UNSIGNED_LONG
                page_addr = self.page_addr(address)
                page_end = page_addr + objects * size
                if dict_enabled is True:
                    page_addrs[address] = (page_addr, page_end)
                else:
                    page_addrs.append((page_addr, page_end))

        return page_addrs

    def get_slab_address(self, chunk_addr, name=None):
        """Get the slab address (struct page*) holding a given chunk address

        @param chunk_addr: a chunk address we are looking for
        @param name: slab cache name if known (optional)
        @return the slab address (struct page*) holding that chunk"""

        if not name:
            slab_caches = Slub.iter_slab_caches()
        else:
            slab_cache = Slub.find_slab_cache(name)
            if slab_cache is None:
                print("Slab cache '%s' not found" % name)
                return None
            slab_caches = [slab_cache]

        for slab_cache in slab_caches:
            pages = self.get_slabs(
                slab_cache
            )  # these are actual "struct page*" (gdb.Value) representing a slab

            for page in pages:
                objects = int(page["objects"]) & Slub.UNSIGNED_INT
                size = int(slab_cache["size"])
                address = int(page.address) & Slub.UNSIGNED_LONG
                page_addr = self.page_addr(address)
                page_end = page_addr + objects * size
                if chunk_addr >= page_addr and chunk_addr < page_end:
                    return address

        return None

    @staticmethod
    def print_slab_cache_pages(name, pages):
        pages.sort()
        last_page = 0
        print(f"{name} has {len(pages)} memory pages:")
        for page in pages:
            if last_page == page - 4096:
                print(f"0x{page:08x}*")
            else:
                print(f"0x{page:08x}")
            last_page = page

    @staticmethod
    def print_slab_cache_pages_ranges(name, pages):
        pages.sort()
        last_page = 0
        print(f"{name} has {len(pages)} memory pages:")
        for start_addr, end_addr in pages:
            if last_page == start_addr - 4096:
                print(f"0x{start_addr:08x}-0x{end_addr:08x}*")
            else:
                print(f"0x{start_addr:08x}-0x{end_addr:08x}")
            last_page = start_addr
