import struct
import sys
import importlib
import logging

import libslub.frontend.printutils as pu
importlib.reload(pu)
import libslub.slub.heap_structure as hs
importlib.reload(hs)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.slub.kmem_cache_cpu as kcc
importlib.reload(kcc)
import libslub.slub.kmem_cache_node as kcn
importlib.reload(kcn)
import libslub.slub.page as p
importlib.reload(p)

log = logging.getLogger("libslub")
log.trace("sbcache.py")

class kmem_cache(hs.heap_structure):
    """python representation of a struct kmem_cache
    
    struct kmem_cache {: https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L90"""

    def __init__(self, sb, value=None, address=None):
        """
        Parse kmem_cache's data and initialize the kmem_cache object

        :param sb: slab object holding all our useful info
        :param value: gdb.Value of type kmem_cache with structure's content read from the debugger (represented by a dictionary)
        :param address: address for a kmem_cache where to read the structure's content from the debugger (not supported yet)
        """

        super(kmem_cache, self).__init__(sb)

        # kmem_cache structure's fields can be looked up directly from the gdb.Value
        self.value = value # gdb.Value representing the kmem_cache

        self.init()

    def init(self):

        # our own abstraction fields
        self.address = int(self.value.address) & sb.sb.UNSIGNED_LONG
        self.name = self.value["name"].string() # slab cache name (e.g. "kmalloc-1k")
        log.debug(f"kmem_cache.init({self.name})")
        self.flags = int(self.value["flags"]) & sb.sb.UNSIGNED_LONG
        self.offset = int(self.value["offset"]) # Free pointer offset
        self.size = int(self.value["size"]) # The size of an object including metadata
        self.object_size = int(self.value["object_size"]) # The size of an object without metadata

        self.kmem_cache_cpu_list = [] # list of kmem_cache_cpu objects for that kmem_cache
        # browse the list of gdb.Value (representing the kmem_cache_cpu structure linked list for that kmem_cache)
        for cpu_id, cache_cpu_value in enumerate(self.sb.get_all_slab_cache_cpus(self.value)):
            kmem_cache_cpu = kcc.kmem_cache_cpu(self.sb, cpu_id, self, cache_cpu_value)
            self.kmem_cache_cpu_list.append(kmem_cache_cpu)


        self.kmem_cache_node_list = [] # list of kmem_cache_node objects for that kmem_cache
        for node_id in range(self.sb.node_num):
            node_value = self.value["node"][node_id] # gdb.value representing kmem_cache->node[node_id] (struct kmem_cache_node *)
            kmem_cache_node = kcn.kmem_cache_node(self.sb, node_id, kmem_cache=self, value=node_value)
            self.kmem_cache_node_list.append(kmem_cache_node)

        # NOTE: There will only be full slabs if one of the following condition is met:
        # - there is/was a watch on a given slab. See 'slab watch' command logic for details
        # - slabs were logged with the sbslabdb command
        # XXX - Ideally we would need to track the full slabs per kmem_cache_node
        # but we don't have that granularity yet
        self.full_slabs = [] # the full slabs
        full_slabs_values = list(self.sb.get_full_slabs(self.name))
        slab_count = len(full_slabs_values)
        for slab_index, full_slab_value in enumerate(full_slabs_values):
            full_slab = p.page(self.sb, self, None, None, sb.SlabType.FULL_SLAB, index=slab_index+1, count=slab_count, value=full_slab_value)
            self.full_slabs.append(full_slab)

    def print(self, verbose=0, use_cache=False, cmd=None):
        """Pretty printer for the kmem_cache supporting different level of verbosity

        :param verbose: 0 for non-verbose. 1 for more verbose. 2 for even more verbose.
        :param use_cache: True if we want to use the cached information from the cache object.
                          False if we want to fetch the data again
        :param cmd: cmd.args == arguments so we know what options have been passed by the user
                     e.g. to print hexdump of objects/chunks, highlight chunks, etc.
        """

        if cmd.args.object_only is not True:
            title = "struct kmem_cache @ 0x%x {" % self.address
            txt = pu.color_title(title)
            txt += "\n  {:11} = ".format("name")
            txt += pu.color_value("{:s}".format(self.name))
            txt += "\n  {:11} = ".format("flags")
            flags_list = sb.sb.get_flags_list(self.flags)
            if flags_list:
                txt += pu.color_value("{:s}".format(" | ".join(flags_list)))
            else:
                txt += pu.color_value("(none)")

            txt += "\n  {:11} = ".format("offset")
            txt += pu.color_value("{:#x}".format(self.offset))
            txt += "\n  {:11} = ".format("size")
            txt += pu.color_value("{:#d} ({:#x})".format(self.size, self.size))
            txt += "\n  {:11} = ".format("object_size")
            txt += pu.color_value("{:#d} ({:#x})".format(self.object_size, self.object_size))
            txt += "\n"
            print(txt, end="")

        for kmem_cache_cpu in self.kmem_cache_cpu_list:
            # do not print when a cpu has no slab,
            # especially useful with threadripper
            if kmem_cache_cpu.main_slab == None:
                continue
            if (cmd.output_filtered is False or cmd.args.main_slab is True or cmd.args.partial_slab is True) and \
                (cmd.args.cpu is None or int(cmd.args.cpu) == kmem_cache_cpu.cpu_id):
                kmem_cache_cpu.print(indent=2, cmd=cmd)

        for kmem_cache_node in self.kmem_cache_node_list:
            if (cmd.cpu_filtered is False and cmd.output_filtered is False) or cmd.args.node_slab is True:
                kmem_cache_node.print(indent=2, cmd=cmd)

        if (cmd.cpu_filtered is False and cmd.output_filtered is False) or cmd.args.full_slab is True:
            # XXX - Ideally we would need to track the full slabs per kmem_cache_node
            # but we don't have that granularity yet
            if cmd.args.object_only is not True:
                txt = "  "
                title = "struct kmem_cache_node @ unknown {"
                txt += pu.color_title(title)
                txt += "\n"
                print(txt, end="")
            if len(self.full_slabs) == 0:
                if cmd.args.object_only is not True:
                    print("    {:8} = (none)".format("full"))
            else:
                for full_slab in self.full_slabs:
                    full_slab.print(name="full", indent=4, cmd=cmd)