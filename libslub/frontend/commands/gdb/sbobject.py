from __future__ import print_function

import argparse
import binascii
import struct
import sys
import logging
import os
import importlib
import gdb

import libslub.frontend.printutils as pu
importlib.reload(pu)
import libslub.slub.kmem_cache as kc
importlib.reload(kc)
import libslub.slub.obj as obj
importlib.reload(obj)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.frontend.helpers as h
importlib.reload(h)
import libslub.frontend.commands.gdb.sbmeta as sbmeta
importlib.reload(sbmeta)
import libslub.frontend.commands.gdb.sbcmd as sbcmd
#importlib.reload(sbcmd)

log = logging.getLogger("libslub")
log.trace("sbobject.py")

class sbobject(sbcmd.sbcmd):
    """Command to print information about objects aka chunk(s) inside a memory region
    associated with a slab.
    
    There are a couple of quirks to know. Other commands can share lots of
    arguments and features with the "sbobject" command. It would have make
    sense to inherit the other command classes from the "sbobject" class, however we 
    would have the same problem as with the "sbcmd" where we can't reload the 
    "sbobject.py" file without restarting gdb. This would have been annoying so 
    we work around that by having some methods of the "sbobject" class defined as 
    static methods and we just call into these from the other command classes
    This is less "clean" but eases a lot development.
    """

    search_types = ["string", "byte", "word", "dword", "qword"]

    def __init__(self, sb):
        log.debug("sbobject.__init__()")
        super(sbobject, self).__init__(sb, "sbobject")

        self.parser = argparse.ArgumentParser(
            description="""Print the metadata and contents of one or more objects/chunks 

Can provide you with a summary of a chunk (one-line) or more verbose information 
in multiple lines (e.g. hexdump of the object contents). 
You can also list information of multiple chunks, search chunks, etc.
""", 
            add_help=False, 
            formatter_class=argparse.RawTextHelpFormatter,
            epilog="""E.g.
sbobject mem-0x10 -v -x -M "tag, backtrace"
sbobject mem-0x10 -M "backtrace:5"

Allocated/free flag: M=allocated, F=freed""")

        sbobject.add_arguments(self)
    
    @staticmethod
    def add_arguments(self):
        """Most arguments are shared by the "sbobject" commands and other commands.
        This function allows to initialize them in other commands too
        
        E.g. if we created a "sbcache" class, we will add arguments later
        after we create our own parser

        Note that it is a static method but it has self as a first
        argument to make it easier to read its implementation
        """
        if self.name == "sbobject":
            group = self.parser
        else:
            group = self.parser.add_argument_group("generic optional arguments")
        if self.name == "sbobject":
            self.parser.add_argument(
                "addresses", nargs="*", default=None,
                help="Address(es) to object(s)/chunk(s) in a memory region associated with a slab"
            )
        self.parser.add_argument(
            "-n",
            dest="name",
            default=None, # None means search in all slab caches
            help="The slab cache name (e.g. kmalloc-64). Use \"sblist\" to get them all",
        )
        group.add_argument(
            "-v", "--verbose", dest="verbose", action="count", default=0,
            help="Use verbose output (multiple for more verbosity)"
        )
        group.add_argument(
            "-h", "--help", dest="help", action="store_true", default=False,
            help="Show this help"
        )
        if self.name == "sbobject":
            group.add_argument(
                "-c", "--count", dest="count", type=h.check_count_value, default=1,
                help="""Number of objects/chunks to print linearly (also supports "unlimited"/0
or negative numbers to print objects/chunks going backwards)"""
            )
        group.add_argument(
            "-x", "--hexdump", dest="hexdump", action="store_true", default=False,
            help="Hexdump the object/chunk contents"
        )
        group.add_argument(
            "-X", dest="hexdump_unit", type=h.check_hexdump_unit, default=1,
            help=f"Specify hexdump unit ({h.prepare_list(h.hexdump_units)}) when using -x (default: %(default)s)"
        )
        group.add_argument(
            "-m", "--maxbytes", dest="maxbytes", type=h.string_to_int, default=0,
            help="Max bytes to dump with -x"
        )
        if self.name == "sbobject" or self.name == "sbcache":
            group.add_argument(
                "-N", dest="no_newline", action="store_true", default=False,
                help="Do not output the trailing newline (summary representation)"
            )
        group.add_argument(
            "-p", dest="print_offset", type=h.string_to_int, default=0,
            help="Print data inside at given offset (summary representation)"
        )
        group.add_argument(
            "-M", "--metadata", dest="metadata", type=str, default=None,
            help="Comma separated list of metadata to print (previously stored with the 'sbmeta' command)"
        )
        if self.name == "sbobject" or self.name == "sbcache":
            group.add_argument(
                "-I", "--highlight-types", dest="highlight_types", type=str, default=None,
                help="Comma separated list of chunk types (M, F) for objects/chunks we want to highlight in the output"
            )
        group.add_argument(
            "-H", "--highlight-addresses", dest="highlight_addresses", type=str, default=None,
            help="Comma separated list of addresses for objects/chunks we want to highlight in the output"
        )
        group.add_argument(
            "-G", "--highlight-metadata", dest="highlight_metadata", type=str, default=None,
            help="""Comma separated list of metadata (previously stored with the 'sbmeta' command) 
for objects/chunks we want to highlight in the output"""
        )
        group.add_argument(
            "--highlight-only", dest="highlight_only", action="store_true", default=False,
            help="Only show the highlighted objects/chunks (instead of just '*' them)"
        )
        if self.name != "sbfree":
            group.add_argument(
                "--use-cache", dest="use_cache", action="store_true", default=False,
                help="""Do not fetch any internal slab data if you know they haven't changed since
last time they were cached"""
            )
        group.add_argument(
            "-s", "--search", dest="search_value", type=str, default=None,
            help="Search a value and show match/no match"
        )
        group.add_argument(
            "-S", "--search-type", dest="search_type", type=str, default="string",
            help=f"Specify search type ({h.prepare_list(sbobject.search_types)}) when using -s (default: %(default)s)"
        )
        group.add_argument(
            "--match-only", dest="match_only", action="store_true", default=False,
            help="Only show the matched chunks (instead of just show match/no match)"
        )
        group.add_argument(
            "--skip-header", dest="skip_header", action="store_true", default=False,
            help="Don't include chunk header contents in search results"
        )
        group.add_argument(
            "--depth", dest="search_depth", type=h.string_to_int, default=0,
            help="How far into each chunk to search, starting from chunk header address"
        )
        group.add_argument(
            "--cmds", dest="commands", type=str, default=None,
            help="""Semi-colon separated list of debugger commands to be executed for each chunk that is displayed 
('@' is replaced by the chunk address)"""
        )
        group.add_argument(
            "--object-info", dest="object_info", action="store_true", default=False,
            help="Show object info such as its slab/cpu/node/etc. (summary representation)"
        )
        # allows to enable a different log level during development/debugging
        self.parser.add_argument(
            "--loglevel", dest="loglevel", default=None,
            help=argparse.SUPPRESS
        )
        # Debug and force printing stuff
        self.parser.add_argument(
            "-d", "--debug", dest="debug", action="store_true", default=False,
            help=argparse.SUPPRESS
        )
        group.add_argument(
            "-o", "--address-offset", dest="address_offset", action="store_true", default=False,
            help="Print offsets from the first printed chunk instead of addresses"
        )

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbobject.invoke()")

        self.sb.cache.update_all(name=self.args.name, show_status=self.args.debug, use_cache=self.args.use_cache)

        log.debug("sbobject.invoke() (2)")

        sbobject.prepare_args_if_negative_count(self)

        ret = sbobject.parse_arguments(self)
        if ret == None:
            return
        addresses, highlight_addresses, highlight_metadata, highlight_types = ret

        # we enforced updating the cache once above so no need to do it for every chunk
        chunks = sbobject.parse_many2(
            self, 
            addresses, 
            highlight_addresses=highlight_addresses, 
            highlight_metadata=highlight_metadata, 
            highlight_types=highlight_types, 
            use_cache=True,
            is_region=True,
        )

    @staticmethod 
    def prepare_args_if_negative_count(self):
        """This is a little bit of a hack. The idea is to handle cases
        where the user wants to print N chunks going backwards.
        We are going to list all the chunks in the memory region associated with
        a slab until we find all the addresses requested and then craft new arguments 
        as if the user requested to print from new addresses N chunks before the requested
        addresses before calling parse_many2()
        """

        self.args.reverse = False
        # Nothing to do if the count is positive or unlimited
        if self.args.count == None or self.args.count >= 0:
            return
        # We are making the count positive
        self.args.count = self.args.count*-1
        # And we print N chunks before the requested chunk + the actual chunk
        self.args.count += 1
        
        addresses = self.dbg.parse_address(self.args.addresses)
        if len(addresses) == 0:
            pu.print_error("WARNING: No valid address supplied")
            self.parser.print_help()
            return

        # We will fill it with new addresses later below
        self.args.addresses = []

        # In what slab caches to look for objects?
        name = self.args.name
        if name != None and name in self.sb.cache.slab_caches.keys():
            kmem_caches = [self.sb.cache.slab_caches[name]]
        elif name == None:
            kmem_caches = list(self.sb.cache.slab_caches.values())

        # Prepare arguments for "sbobject" format
        # i.e. for every address, get the new address N chunks before
        for addr in addresses:
            ret = obj.obj.is_object_address_in_slab_caches(kmem_caches, addr)
            if ret is None and name != None:
                pu.print_error(f"WARNING: Could not find {addr:#x} in slab cache, skipping")
                continue
            (index, objects_list) = ret
            index -= (self.args.count-1)
            if index < 0:
                pu.print_error(f"WARNING: Reaching beginning of memory region with {addr:#x}")
                index = 0
            self.args.addresses.append(f"{objects_list[index].address:#x}")

    @staticmethod
    def parse_arguments(self):
        log.debug("sbobject.parse_arguments()")
        addresses = []
        if not self.args.addresses:
            print("WARNING: No address supplied?")
            #self.parser.print_help()
            return None
        else:
            addresses = self.dbg.parse_address(self.args.addresses)
            if len(addresses) == 0:
                pu.print_error("WARNING: No valid address supplied")
                #self.parser.print_help()
                return None

        if self.args.hexdump_unit not in h.hexdump_units:
            pu.print_error("Wrong hexdump unit specified")
            #self.parser.print_help()
            return None

        if self.args.name != None and self.args.name not in self.sb.cache.slab_caches.keys():
            pu.print_error(f"Wrong slab cache name specified {self.args.name}")
            #self.parser.print_help()
            return None

        if self.args.search_type not in sbobject.search_types:
            pu.print_error(f"Wrong search type specified {self.args.search_type}")
            #self.parser.print_help()
            return None
        if self.args.search_type != "string" and not self.args.search_value.startswith("0x"):
            pu.print_error("Wrong search value for specified type")
            #self.parser.print_help()
            return None

        highlight_addresses = []
        if self.args.highlight_addresses:
            list_highlight_addresses = [e.strip() for e in self.args.highlight_addresses.split(",")]
            highlight_addresses = self.dbg.parse_address(list_highlight_addresses)
            if len(highlight_addresses) == 0:
                pu.print_error("WARNING: No valid address to highlight supplied")
                #self.parser.print_help()
                return None
        highlight_metadata = []
        if self.args.highlight_metadata:
            highlight_metadata = [e.strip() for e in self.args.highlight_metadata.split(",")]

        # some commands inheriting sbobject arguments don't support highlighting types
        try:
            highlight_types = self.args.highlight_types
        except AttributeError:
            highlight_types = None
        if highlight_types:
            highlight_types = [e.strip() for e in highlight_types.split(",")]
            for e in highlight_types:
                if e not in ["M", "F"]:
                    pu.print_error("WARNING: Invalid type to highlight supplied")
                    #self.parser.print_help()
                    return None
        else:
            highlight_types = []
        
        return addresses, highlight_addresses, highlight_metadata, highlight_types

    @staticmethod
    def parse_many2(self,
        addresses, 
        highlight_addresses=[], 
        highlight_metadata=[], 
        highlight_types=[],
        inuse=None,
        main_slab_freelist=None,
        allow_invalid=False,
        separate_addresses_non_verbose=True,
        header_once=None,
        count_handle=None,
        count_printed=None,
        use_cache=False, 
        is_region=False,
        is_freelist=False,
    ):
        """Most arguments are shared by "sbobject" and other commands.
        This function allows for other commands to call into "sbobject"

        :param inuse: True if we know it is an inuse chunk (i.e. not in any bin) (not required)
        :param main_slab_freelist: True if we know all the chunks are in the cpu main slab freelist,
                        False if we know they are NOT in the cpu main slab freelist. 
                        None otherwise.
        :param allow_invalid: sometimes these structures will be used for
                              that isn't actually a complete chunk, like a freebin, in these cases we
                              still wanted to be able to parse so that we can access the forward and
                              backward pointers, so shouldn't complain about their being invalid size
        :param separate_addresses_non_verbose: False to avoid a separation when printing
                                               one-line chunks, like in feelists
        :param header_once: string to print before printing the first chunk, or None if not needed
        :param count_handle: maximum number of chunks to handle per address, even if not printed, or None if unlimited
        :param count_printed: maximum number of chunks to print in total for all addresses, or None if unlimited.
                              Only useful if handling a freebin.
        :return: the list of objects found

        Note that it is a static method but it has self as a first
        argument to make it easier to read its implementation
        """

        hexdump_unit = self.args.hexdump_unit
        count = self.args.count
        search_depth = self.args.search_depth
        skip_header = self.args.skip_header
        print_offset = self.args.print_offset
        metadata = self.args.metadata
        verbose = self.args.verbose
        no_newline = self.args.no_newline
        debug = self.args.debug
        hexdump = self.args.hexdump
        maxbytes = self.args.maxbytes
        commands = self.args.commands
        address_offset = self.args.address_offset

        name = self.args.name

        search_value = self.args.search_value
        search_type = self.args.search_type
        match_only = self.args.match_only

        highlight_only = self.args.highlight_only
        object_info = self.args.object_info

        # In what slab caches to look for objects?
        if name != None and name in self.sb.cache.slab_caches.keys():
            kmem_caches = [self.sb.cache.slab_caches[name]]
        elif name == None:
            kmem_caches = list(self.sb.cache.slab_caches.values())

        all_chunks = []
        chunks = None
        for address in addresses:
            if chunks is not None and len(chunks) > 0 and \
            (separate_addresses_non_verbose or verbose > 0):
                print("-" * 60)

            if count_printed == None:
                count_linear = count
            elif count == None:
                count_linear = count_printed
            else:
                count_linear = min(count_printed, count)

            ret = obj.obj.is_object_address_in_slab_caches(kmem_caches, address)
            if ret is None:
                return
            (index, objects_list) = ret

            chunks = sbobject.parse_many(
                objects_list, 
                index, 
                self.sb, 
                self.dbg, 
                count_linear, 
                count_handle, 
                search_depth,
                skip_header, 
                hexdump_unit, 
                search_value, 
                search_type, 
                match_only, 
                print_offset, 
                verbose,
                no_newline,
                debug, 
                hexdump, 
                maxbytes, 
                metadata,
                highlight_types=highlight_types,
                highlight_addresses=highlight_addresses,
                highlight_metadata=highlight_metadata,
                highlight_only=highlight_only,
                inuse=inuse, 
                allow_invalid=allow_invalid,
                header_once=header_once, 
                commands=commands,
                use_cache=use_cache,
                address_offset=address_offset,
                name=name,
                is_region=is_region,
                is_freelist=is_freelist,
                object_info=object_info,
            )
            if chunks is not None and len(chunks) > 0:
                all_chunks.extend(chunks)
                if count_printed != None:
                    count_printed -= len(chunks)
                header_once = None
            if count_printed == 0:
                break
        return all_chunks

    # XXX - probably sb can just have the debugger
    @staticmethod
    def parse_many(
        objects_list, 
        index, 
        sb, 
        dbg=None, 
        count=1, 
        count_handle=None, 
        search_depth=0, 
        skip_header=False, 
        hexdump_unit=1, 
        search_value=None,
        search_type=None, 
        match_only=False, 
        print_offset=0, 
        verbose=0, 
        no_newline=False,
        debug=False, 
        hexdump=False, 
        maxbytes=0, 
        metadata=None,
        highlight_types=[], 
        highlight_addresses=[], 
        highlight_metadata=[], 
        highlight_only=False, 
        inuse=None, 
        allow_invalid=False,
        header_once=None, 
        commands=None,
        use_cache=False, 
        address_offset=False, 
        name=None,
        indent="",
        is_region=False,
        is_freelist=False,
        object_info=False,
    ):
        """Parse many chunks starting from a given address and show them based
        passed arguments

        :param objects_list: list of objects (linear view for memory regions or freelist)
        :param index: index in objects_list[] to start parsing from
        :param sb: slab object (libslub constants and helpers)
        :param dbg: pydbg object (debugger interface)
        :param count: see sbobject's ArgumentParser definition
                      maximum number of chunks to print, or None if unlimited
        :param count_handle: maximum number of chunks to handle per address, even if not printed, or None if unlimited
        :param search_depth: see sbobject's ArgumentParser definition
        :param skip_header: see sbobject's ArgumentParser definition
        :param hexdump_unit: see sbobject's ArgumentParser definition
        :param search_value: see sbobject's ArgumentParser definition
        :param search_type: see sbobject's ArgumentParser definition
        :param match_only: see sbobject's ArgumentParser definition
        :param print_offset: see sbobject's ArgumentParser definition
        :param verbose: see sbobject's ArgumentParser definition
        :param no_newline: see sbobject's ArgumentParser definition
        :param debug: see sbobject's ArgumentParser definition
        :param hexdump: see sbobject's ArgumentParser definition
        :param maxbytes: see sbobject's ArgumentParser definition
        :param metadata: see sbobject's ArgumentParser definition
        :param highlight_types: list of types. highlight chunks with matching type with a '*' e.g. to be used by 'ptlist'
        :param highlight_addresses: list of addresses. highlight chunks with matching address with a '*' e.g. to be used by 'ptlist'
        :param highlight_metadata: list of metadata. highlight chunks with matching metadata with a '*' e.g. to be used by 'ptlist'
        :param highlight_only: see sbobject's ArgumentParser definition
        :param inuse: True if we know all the chunks are inuse (i.e. not in any bin)
                      False if we know they are NOT in inuse.
                      None otherwise.
                      Useful to specify when parsing a regular bin
        :param allow_invalid: sometimes these structures will be used for
                              that isn't actually a complete chunk, like a freebin, in these cases we
                              still wanted to be able to parse so that we can access the forward and
                              backward pointers, so shouldn't complain about their being invalid size
        :param header_once: string to print before printing the first chunk, or None if not needed
        :param commands: see sbobject's ArgumentParser definition
        :param use_cache: see sbobject's ArgumentParser definition
        :param address_offset: see sbobject's ArgumentParser definition
        :param name: see sbobject's ArgumentParser definition

        :return: the list of malloc_chunk being parsed and already shown
        """
        chunks = []
        if len(objects_list) == 0 or index >= len(objects_list):
            return chunks

        highlight_types = set(highlight_types)
        for t in highlight_types:
            if t != "M" and t != "F":
                print("ERROR: invalid chunk type provided, should not happen")
                return []
        highlight_addresses = set(highlight_addresses)
        highlight_metadata = set(highlight_metadata)
        highlight_metadata_found = set([])

        count_objects = len(objects_list)

        o = objects_list[index]
        first_address = o.address
        dump_offset = 0
        while True:
            prefix = "" # used for one-line output
            suffix = "" # used for one-line output
            epilog = "" # used for verbose output

            if object_info:
                show_slab_cache = name is None
                suffix += f" ({o.info(show_slab_cache=show_slab_cache)})"

            colorize_func = str # do not colorize by default
            if metadata is not None:
                opened = False
                list_metadata = [e.strip() for e in metadata.split(",")]
                L, s, e, colorize_func = sbmeta.get_metadata(o.address, list_metadata=list_metadata)
                suffix += s
                epilog += e
                o.metadata = L # save so we can easily export to json later

            if search_value is not None:
                if not dbg.search_chunk(
                    sb, o, search_value, search_type=search_type,
                    depth=search_depth, skip=skip_header
                ):
                    found_match = False
                    suffix += " [NO MATCH]"
                else:
                    suffix += pu.light_green(" [MATCH]")
                    found_match = True

            # XXX - the current representation is not really generic as we print the first short
            # as an ID and the second 2 bytes as 2 characters. We may want to support passing the
            # format string as an argument but this is already useful
            if print_offset != 0:
                mem = dbg.read_memory(
                    o.address + print_offset, 4
                )
                (id_, desc) = struct.unpack_from("<H2s", mem, 0x0)
                if h.is_ascii(desc):
                    suffix += " 0x%04x %s" % (id_, str(desc, encoding="utf-8"))
                else:
                    suffix += " 0x%04x hex(%s)" % (
                        id_,
                        str(binascii.hexlify(desc), encoding="utf-8"),
                    )

            if is_region:
                if index == 0:
                    suffix += " (region start)"
                elif index == count_objects-1:
                    suffix += " (region end)"
            if is_freelist:
                suffix += f" [{index+1:#d}]"

            # Only print the chunk type for non verbose
            printed = False
            if verbose == 0:
                found_highlight = False
                # Only highlight chunks for non verbose
                if o.address in highlight_addresses:
                    found_highlight = True
                    highlight_addresses.remove(o.address)
                if (o.inuse is True and "M" in highlight_types) or \
                    (o.inuse is False and "F" in highlight_types):
                    found_highlight = True
                if len(highlight_metadata) > 0:
                    # We retrieve all metadata since we want to highlight chunks containing any of the
                    # metadata, even if we don't show some of the metadata
                    _, s, _, _ = sbmeta.get_metadata(o.address, list_metadata="all")
                    for m in highlight_metadata:
                        # we check in the one-line output as it should have less non-useful information
                        if m in s:
                            found_highlight = True
                            highlight_metadata_found.add(m)
                if found_highlight:
                    prefix += "* "
                if (not highlight_only or found_highlight) \
                    and (not match_only or found_match):
                    if header_once != None:
                        print(indent + header_once)
                        header_once = None
                    if no_newline:
                        print(indent + prefix + o.to_string(colorize_func=colorize_func) + suffix, end="")
                    else:
                        print(indent + prefix + o.to_string(colorize_func=colorize_func) + suffix)
                    printed = True
            elif verbose >= 1 and (not match_only or found_match):
                if header_once != None:
                    print(indent + header_once)
                    header_once = None
                print(indent + o)
                printed = True
            if printed:
                if hexdump:
                    dbg.print_hexdump_chunk(sb, o, maxlen=maxbytes, off=dump_offset, unit=hexdump_unit, verbose=verbose)
                if verbose >= 1 and epilog:
                    print(indent + epilog, end="")
                if commands:
                    for command in commands.split(";"):
                        formatted_command = command.replace("@", f"{o.address:#x}")
                        if no_newline:
                            print(indent + dbg.execute(formatted_command), end="")
                        else:
                            print(indent + dbg.execute(formatted_command))
                chunks.append(o)
                if count != None:
                    count -= 1
            if count_handle != None:
                count_handle -= 1
            index += 1
            if count != 0 and count_handle != 0:
                if printed and (verbose >= 1 or hexdump):
                    print(indent+"--")
                if index == count_objects:
                    # Only print the chunk type for non verbose
                    print("Stopping due to end of memory region")
                    break
                o = objects_list[index]
            else:
                break

        # XXX - can't really show that atm as we have lots of memory regions
        # each associated with a given slab, so would spam messages
        #if len(highlight_addresses) != 0:
        #    pu.print_error("WARNING: Could not find these chunk addresses: %s" % (", ".join(["0x%x" % x for x in highlight_addresses])))
        #if len(highlight_metadata-highlight_metadata_found) != 0:
        #    pu.print_error("WARNING: Could not find these metadata: %s" % (", ".join(list(highlight_metadata-highlight_metadata_found))))

        return chunks