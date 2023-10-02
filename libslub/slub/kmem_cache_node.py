import gdb

import libslub.frontend.printutils as pu
import libslub.slub.heap_structure as hs
import libslub.slub.page as p
import libslub.slub.sb as sb


class kmem_cache_node(hs.heap_structure):
    """python representation of a struct kmem_cache_node

    struct kmem_cache_node {: https://elixir.bootlin.com/linux/v5.15/source/mm/slab.h#L533
    """

    def __init__(self, sb, node_id, kmem_cache, value=None, address=None):
        """
        Parse kmem_cache_node's data and initialize the kmem_cache_node object

        :param sb: slab object holding all our useful info
        :param value: gdb.Value of type kmem_cache_node with structure's content read from the debugger (represented by a dictionary)
        :param address: address for a kmem_cache_node where to read the structure's content from the debugger (not supported yet)
        """

        super(kmem_cache_node, self).__init__(sb)

        # kmem_cache_node structure's fields can be looked up directly from the gdb.Value
        self.value = value  # gdb.Value representing the kmem_cache_node
        self.kmem_cache = kmem_cache  # kmem_cache object

        self.init(node_id)

    def init(self, node_id):
        # our own abstraction fields
        self.node_id = node_id  # node index in the kmem_cache
        self.address = int(self.value.address) & sb.Slub.UNSIGNED_LONG

        self.partial_slabs = []  # list of kmem_cache_cpu objects for that kmem_cache
        # browse the list of gdb.Value (representing the kmem_cache_cpu->node[node_id].partial linked list of struct page*)
        page_type = gdb.lookup_type("struct page")
        partial_slabs_values = list(
            self.sb.for_each_entry(page_type, self.value["partial"], "lru")
        )
        slab_count = len(partial_slabs_values)
        for slab_index, slab_value in enumerate(partial_slabs_values):
            partial_slab = p.page(
                self.sb,
                self.kmem_cache,
                None,
                self,
                sb.SlabType.NODE_SLAB,
                index=slab_index + 1,
                count=slab_count,
                value=slab_value,
            )
            self.partial_slabs.append(partial_slab)

    def print(self, verbose=0, use_cache=False, indent=0, cmd=None):
        """Pretty printer for the kmem_cache_node supporting different level of verbosity

        :param verbose: 0 for non-verbose. 1 for more verbose. 2 for even more verbose.
        :param use_cache: True if we want to use the cached information from the cache object.
                          False if we want to fetch the data again
        :param cmd: cmd.args == arguments so we know what options have been passed by the user
                     e.g. to print hexdump of objects/chunks, highlight chunks, etc.
        """

        if cmd.args.object_only is not True:
            txt = " " * indent
            title = "struct kmem_cache_node @ 0x%x (node %d) {" % (
                self.address,
                self.node_id,
            )
            txt += pu.color_title(title)
            txt += "\n"
            print(txt, end="")

        if len(self.partial_slabs) == 0:
            if cmd.args.object_only is not True:
                print("{:s}  partial = (none)".format(" " * indent))
        else:
            for partial_slab in self.partial_slabs:
                partial_slab.print(name="partial", indent=indent + 2, cmd=cmd)
