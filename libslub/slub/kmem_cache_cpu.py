import struct
import sys
import importlib

import libslub.frontend.printutils as pu
importlib.reload(pu)
import libslub.slub.heap_structure as hs
importlib.reload(hs)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.slub.slab as p
importlib.reload(p)
import libslub.slub.obj as obj
importlib.reload(obj)
import libslub.frontend.commands.gdb.sbobject as sbobject
importlib.reload(sbobject)


class kmem_cache_cpu(hs.heap_structure):
    """python representation of a struct kmem_cache_cpu
    
    struct kmem_cache_cpu {: https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L48
    """

    def __init__(self, sb, cpu_id, kmem_cache, value=None, address=None):
        """
        Parse kmem_cache_cpu's data and initialize the kmem_cache_cpu object

        :param sb: slab object holding all our useful info
        :param value: gdb.Value of type kmem_cache_cpu with structure's content read from the debugger (represented by a dictionary)
        :param address: address for a kmem_cache_cpu where to read the structure's content from the debugger (not supported yet)
        """

        super(kmem_cache_cpu, self).__init__(sb)

        # kmem_cache_cpu structure's fields can be looked up directly from the gdb.Value
        self.value = value # gdb.Value representing the kmem_cache_cpu
        self.kmem_cache = kmem_cache # kmem_cache object

        self.init(cpu_id)

    def init(self, cpu_id):
        

        # our own abstraction fields
        self.cpu_id = cpu_id # CPU index in the kmem_cache
        self.address = int(self.value.address) & sb.sb.UNSIGNED_LONG
        self.fp = int(self.value["freelist"]) & sb.sb.UNSIGNED_LONG # freelist head address
        freelist_addresses = list(sb.sb.walk_freelist(self.kmem_cache.value, self.fp)) # list of addresses
        self.freelist = []
        for address in freelist_addresses:
            # we pass None as the page as it is not built yet but we'll update it after creating the main slab
            o = obj.obj(self.sb, address, self.kmem_cache, self, None, None, inuse=False)
            self.freelist.append(o)

        page_or_slab = self.sb.kcl.slab_or_page

        # the slab from which we are allocating for that cpu core
        self.main_slab = None
        if self.value[page_or_slab]:
            self.main_slab = p.slab(self.sb, self.kmem_cache, self, None, sb.SlabType.MAIN_SLAB, value=self.value[page_or_slab].dereference(), is_main_slab=True)

        # update the main freelist's objects "slab"
        for o in self.freelist:
            o.page = self.main_slab

        # the partial slabs
        self.partial_slabs = []
        slab_ptr = self.value["partial"]
        slab_count = 0
        while slab_ptr:
            slab_count += 1
            slab = slab_ptr.dereference()
            slab_ptr = slab["next"]
        slab_index = 1
        slab_ptr = self.value["partial"]
        while slab_ptr:
            slab = slab_ptr.dereference()
            partial_slab = p.slab(self.sb, self.kmem_cache, self, None, sb.SlabType.PARTIAL_SLAB, index=slab_index, count=slab_count, value=slab)
            self.partial_slabs.append(partial_slab)
            slab_ptr = slab["next"]
            slab_index += 1

    def print(self, verbose=0, use_cache=False, indent=0, cmd=None):
        """Pretty printer for the kmem_cache_cpu supporting different level of verbosity

        :param verbose: 0 for non-verbose. 1 for more verbose. 2 for even more verbose.
        :param use_cache: True if we want to use the cached information from the cache object.
                          False if we want to fetch the data again
        :param cmd: cmd.args == arguments so we know what options have been passed by the user
                     e.g. to print hexdump of objects/chunks, highlight chunks, etc.
        """

        if cmd.args.object_only is not True:
            txt = " "*indent
            title = "struct kmem_cache_cpu @ 0x%x (cpu %d) {" % (self.address, self.cpu_id)
            txt += pu.color_title(title)
            txt += "\n"
            print(txt, end="")

        # print the objects in the the main freelist
        # it only make sense if we want to show the main slab as are chunked from that main slab
        if cmd.output_filtered is False or cmd.args.main_slab is True or cmd.args.show_lockless_freelist:
            if cmd.args.object_only is not True:
                txt = "{:s}  {:8} = ".format(" "*indent, "freelist")
                txt += pu.color_value("{:#x}".format(self.fp))
                txt += " ({:#d} elements)".format(len(self.freelist))
                txt += "\n"
                print(txt, end="")

            if cmd.args.show_lockless_freelist:
                if cmd.args.object_only is True and cmd.args.hide_title is False:
                    txt = pu.color_value("{:s}  lockless freelist:").format(" "*indent)
                    txt += "\n"
                    print(txt, end="")
                # Prepare arguments for "sbobject" format
                # i.e. the chunks to print are from the freelist

                # The amount of printed addresses will be limited by 
                # parse_many()'s "count" argument
                if cmd.args.count == None:
                    count = len(self.freelist)
                else:
                    count = cmd.args.count

                sbobject.sbobject.parse_many(
                    self.freelist, 
                    0, 
                    cmd.sb, 
                    cmd.dbg, 
                    None, # count
                    count, # count_handle
                    cmd.args.search_depth,
                    cmd.args.skip_header, 
                    cmd.args.hexdump_unit, 
                    cmd.args.search_value, 
                    cmd.args.search_type, 
                    cmd.args.match_only, 
                    cmd.args.print_offset, 
                    cmd.args.verbose, 
                    cmd.args.no_newline,
                    cmd.args.debug, 
                    cmd.args.hexdump, 
                    cmd.args.maxbytes, 
                    cmd.args.metadata,
                    highlight_types=cmd.highlight_types,
                    highlight_addresses=cmd.highlight_addresses,
                    highlight_metadata=cmd.highlight_metadata,
                    highlight_only=cmd.args.highlight_only,
                    commands=cmd.args.commands,
                    use_cache=cmd.args.use_cache,
                    address_offset=cmd.args.address_offset,
                    name=cmd.args.name,
                    indent=" "*(indent+4),
                    is_freelist=True,
                    object_info=cmd.args.object_info,
                )

        page_or_slab = self.sb.kcl.slab_or_page
        if cmd.output_filtered is False or cmd.args.main_slab is True:
            self.main_slab.print(name=page_or_slab, indent=indent+2, cmd=cmd)
        if cmd.output_filtered is False or cmd.args.partial_slab is True:
            for partial_slab in self.partial_slabs:
                partial_slab.print(name="partial", indent=indent+2, cmd=cmd)