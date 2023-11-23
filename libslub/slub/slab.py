from operator import index
import struct
import sys
import importlib

import libslub.frontend.printutils as pu
importlib.reload(pu)
import libslub.slub.heap_structure as hs
importlib.reload(hs)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.slub.obj as obj
importlib.reload(obj)
import libslub.frontend.commands.gdb.sbobject as sbobject
importlib.reload(sbobject)

class slab(hs.heap_structure):
    """python representation of a struct page
    
    struct page {: https://elixir.bootlin.com/linux/v5.15/source/include/linux/mm_types.h#L70
    """

    def __init__(self, sb, kmem_cache, kmem_cache_cpu, kmem_cache_node, type, index=0, count=0, value=None, address=None, is_main_slab=False):
        """
        Parse page's data and initialize the page object

        :param sb: slab object holding all our useful info
        :param value: gdb.Value of type page with structure's content read from the debugger (represented by a dictionary)
        :param address: address for a page where to read the structure's content from the debugger (not supported yet)
        """

        super(slab, self).__init__(sb)

        # slab structure's fields can be looked up directly from the gdb.Value
        self.value = value # gdb.Value representing the page
        self.kmem_cache = kmem_cache # kmem_cache Python object
        self.kmem_cache_cpu = kmem_cache_cpu # kmem_cache_cpu Python object or None
        self.kmem_cache_node = kmem_cache_node # kmem_cache_node Python object or None
        self.type = type   # SlabType enum representing the slab type

        self.init(index, count, is_main_slab)

    def init(self, index, count, is_main_slab):

        # our own abstraction fields
        self.address = int(self.value.address) & sb.sb.UNSIGNED_LONG
        self.index = index # index in the slab linked list (struct page*)
        self.count = count # count of slabs in the linked list (struct page*)
        self.is_main_slab = is_main_slab # boolean to indicate if main slab associated with given cpu
        self.objects = int(self.value["objects"]) & sb.sb.UNSIGNED_INT
        self.inuse = int(self.value["inuse"]) & sb.sb.UNSIGNED_INT
        self.frozen = int(self.value["frozen"])
        self.fp = int(self.value["freelist"]) & sb.sb.UNSIGNED_LONG # freelist head address
        kmem_cache_value = self.value["slab_cache"].dereference() # gdb.Value representing the parent kmem_cache
        
        freelist_addresses = list(sb.sb.walk_freelist(kmem_cache_value, self.fp)) # list of addresses
        self.freelist = []
        for address in freelist_addresses:
            o = obj.obj(self.sb, address, self.kmem_cache, self.kmem_cache_cpu, self.kmem_cache_node, self, inuse=False)
            self.freelist.append(o)
        
        self.region_start = self.sb.page_addr(self.address)
        self.region_end = self.region_start + self.objects*int(kmem_cache_value["size"])
        
        object_addresses = list(sb.sb.walk_linear_memory_region(kmem_cache_value, self.value, self.region_start))
        self.objects_list = []
        for address in object_addresses:
            found = False
            # have unique obj() shared between freelist and objects_list

            # is it the main slab and is the object in the main freelist
            if self.is_main_slab:
                for o in self.kmem_cache_cpu.freelist:
                    if address == o.address:
                        self.objects_list.append(o)
                        found = True
                        break
            if found is True:
                continue
            # is the object tracked in the slab's free list?
            try:
                index = freelist_addresses.index(address)
            except ValueError:
                pass
            else:
                self.objects_list.append(self.freelist[index])
                found = True
            if found is True:
                continue
            # not in any freelist, so creating obj()
            o = obj.obj(self.sb, address, self.kmem_cache, self.kmem_cache_cpu, self.kmem_cache_node, self, inuse=True)
            self.objects_list.append(o)

    def print(self, name="", verbose=0, use_cache=False, indent=0, cmd=None):
        """Pretty printer for the page supporting different level of verbosity

        :param verbose: 0 for non-verbose. 1 for more verbose. 2 for even more verbose.
        :param use_cache: True if we want to use the cached information from the cache object.
                          False if we want to fetch the data again
        :param cmd: cmd.args == arguments so we know what options have been passed by the user
                     e.g. to print hexdump of objects/chunks, highlight chunks, etc.
        """

        if cmd.args.object_only is not True:
            txt = " "*indent
            if name:
                txt += "{:8} = ".format(name)
            if self.is_main_slab:
                title = "struct page @ 0x%x {" % (self.address)
            else:
                title = "struct page @ 0x%x (%d/%d) {" % (self.address, self.index, self.count)
            txt += pu.color_title(title)
            txt += "\n{:s}  {:8} = ".format(" "*indent, "objects")
            txt += pu.color_value("{:#d}".format(self.objects))

            if self.is_main_slab:
                txt += "\n{:s}  {:8} = ".format(" "*indent, "inuse")
                txt += pu.color_value("{:#d}".format(self.inuse))
                # the inuse value is kind of a lie in this case
                txt += " (real = {:#d})".format(self.inuse-len(self.kmem_cache_cpu.freelist))
            else: # partial slab, full slab, etc.
                txt += "\n{:s}  {:8} = ".format(" "*indent, "inuse")
                txt += pu.color_value("{:#d}".format(self.inuse))
            txt += "\n{:s}  {:8} = ".format(" "*indent, "frozen")
            txt += pu.color_value("{:#d}".format(self.frozen))

            txt += "\n{:s}  {:8} = ".format(" "*indent, "freelist")
            txt += pu.color_value("{:#x}".format(self.fp))
            txt += " ({:#d} elements)".format(len(self.freelist))
            txt += "\n"
            print(txt, end="")

        if cmd.args.show_freelist:
            if cmd.args.object_only is True and cmd.args.hide_title is False:
                txt = pu.color_value("{:s}regular freelist:").format(" "*indent)
                txt += "\n"
                print(txt, end="")
            # print the objects in the the freelist

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
                count, # count_handle,
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

        if cmd.args.object_only is not True:
            txt = "{:s}  region   @ {:#x}-{:#x}".format(" "*indent, self.region_start, self.region_end)
            txt += " ({:#d} elements)".format(len(self.objects_list))
            txt += "\n"
            print(txt, end="")

        if cmd.args.show_region:
            if cmd.args.object_only is True and cmd.args.hide_title is False:
                txt = pu.color_value("{:s}  region:").format(" "*indent)
                txt += "\n"
                print(txt, end="")
            # print the linear objects in the the slab
            if cmd.args.count == None:
                count = len(self.objects_list)
            else:
                count = cmd.args.count

            sbobject.sbobject.parse_many(
                self.objects_list, 
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
                is_region=True,
                object_info=cmd.args.object_info,
            )