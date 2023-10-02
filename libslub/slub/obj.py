import libslub.slub.heap_structure as hs
import libslub.slub.kmem_cache as kc
import libslub.slub.sb as sb


class obj(hs.heap_structure):
    """python representation of a chunk/object

    This is not associated to any structure since the object is dependent on the actual data being manipulated
    and not on the SLAB allocator but we track it here to ease manipulating them
    """

    def __init__(
        self, sb, address, kmem_cache, kmem_cache_cpu, kmem_cache_node, page, inuse=None
    ):
        """

        :param sb: slab object holding all our useful info
        :param address: chunk/object address
        :param kmem_cache: kmem_cache Python object
        :param kmem_cache_cpu: kmem_cache_cpu Python object
        :param page: page Python object
        :param inuse: True if we know it is inuse. False if we know it is in a freelist. None if we don't know.
        """

        super(obj, self).__init__(sb)

        self.kmem_cache = kmem_cache  # kmem_cache Python object
        self.kmem_cache_cpu = kmem_cache_cpu  # kmem_cache_cpu Python object or None
        self.kmem_cache_node = kmem_cache_node  # kmem_cache_node Python object or None
        self.page = page  # page Python object
        self.address = address  # address of the chunk/object in memory

        self.init(inuse)

    def init(self, inuse):
        # our own abstraction fields
        self.size = self.kmem_cache.size
        if inuse is None:
            self.inuse = True
            if self.page.is_main_slab:
                cpu_freelist = self.kmem_cache_cpu.freelist
            else:
                cpu_freelist = []  # not applicable
            for o in self.page.freelist:
                if self.address == o.address:
                    self.inuse = False
                    break
            if self.inuse is True:
                for o in cpu_freelist:
                    if self.address == o.address:
                        self.inuse = False
        else:
            self.inuse = inuse

    def __str__(self):
        """Pretty printer for the obj"""
        return self.to_string()

    def to_string(
        self, name="", verbose=0, use_cache=False, indent=0, colorize_func=str
    ):
        """Pretty printer for the obj supporting different level of verbosity

        :param verbose: 0 for non-verbose. 1 for more verbose. 2 for even more verbose.
        :param use_cache: True if we want to use the cached information from the cache object.
                          False if we want to fetch the data again
        """

        txt = ""
        if self.inuse:
            t = "M"
        else:
            t = "F"
        address = "{:#x}".format(self.address)
        txt += "{:s}{:s} {:s}".format(" " * indent, colorize_func(address), t)

        return txt

    def info(self, show_slab_cache=False):
        txt = ""
        if show_slab_cache:
            txt += f"{self.kmem_cache.name} "
        if self.kmem_cache_cpu is not None:
            txt += f"cpu{self.kmem_cache_cpu.cpu_id} "
            if self.page.type == sb.SlabType.MAIN_SLAB:
                txt += "main "
            elif self.page.type == sb.SlabType.PARTIAL_SLAB:
                txt += "partial "
        elif self.kmem_cache_node is not None:
            txt += f"node{self.kmem_cache_node.node_id} "
            if self.page.type == sb.SlabType.NODE_SLAB:
                txt += "partial "
        else:
            if self.page.type == sb.SlabType.FULL_SLAB:
                txt += "full "
        if self.page.count != 0:
            txt += f"{self.page.index}/{self.page.count}"
        else:
            txt = txt[:-1]  # remove ending space
        return txt

    @staticmethod
    def indexof(address, list_objects):
        """Helper to quickly find if a given address is the start of a given chunk/object in a list of obj()

        @param address: an integer address
        @param list_objects: a list of obj()
        @param the index of the obj() starting at address if found, or -1 if not found
        """

        for index, obj in enumerate(list_objects):
            if address == obj.address:
                return index
        return -1

    @staticmethod
    def is_object_address_in_slab_caches(kmem_caches, address):
        """Check if a given address is in one of the memory regions in a given slab cache or multiple slab caches
        @param kmem_caches: a single kmem_cache Python object representing a slab cache or a list of them
        @param address: address we want to check if it is a chunk/object in that slab cache
        @param return a tuple (index, objects_list) where objects_list is the list of obj()
               where the chunk/object address was found and index is the index in objects_list
               where it was found. If it is not found, it returns None instead of the tuple
        """

        if isinstance(kmem_caches, kc.kmem_cache):
            kmem_caches = [kmem_caches]
        elif isinstance(kmem_caches, list):
            pass
        else:
            print(
                "Invalid kmem_caches type passed to is_object_address_in_slab_cache(), should not happen"
            )
            return None

        for kmem_cache in kmem_caches:
            for kmem_cache_cpu in kmem_cache.kmem_cache_cpu_list:
                main_slab = kmem_cache_cpu.main_slab
                # sometimes, a cpu has no slab especially (e.g. with threadripper)
                if main_slab is not None:
                    index = obj.indexof(address, main_slab.objects_list)
                    if index >= 0:
                        return index, main_slab.objects_list
                for partial_slab in kmem_cache_cpu.partial_slabs:
                    index = obj.indexof(address, partial_slab.objects_list)
                    if index >= 0:
                        return index, partial_slab.objects_list
            for kmem_cache_node in kmem_cache.kmem_cache_node_list:
                for partial_slab in kmem_cache_node.partial_slabs:
                    index = obj.indexof(address, partial_slab.objects_list)
                    if index >= 0:
                        return index, partial_slab.objects_list
            for full_slab in kmem_cache.full_slabs:
                index = obj.indexof(address, full_slab.objects_list)
                if index >= 0:
                    return index, full_slab.objects_list
        return None
