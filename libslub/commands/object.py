import argparse
import binascii
import logging
import struct

import libslub.commands.meta as meta
import libslub.debugger
import libslub.frontend.helpers as h
import libslub.frontend.printutils as pu
import libslub.slub.obj as obj
from libslub.frontend.helpers import Options

old_notes = """
    There are a couple of quirks to know. Other commands can share lots of
    arguments and features with the "sbobject" command. It would have make
    sense to inherit the other command classes from the "sbobject" class, however we
    would have the same problem as with the "sbcmd" where we can't reload the
    "sbobject.py" file without restarting gdb. This would have been annoying so
    we work around that by having some methods of the "sbobject" class defined as
    static methods and we just call into these from the other command classes
    This is less "clean" but eases a lot development.
"""

log = logging.getLogger("libslub")
log.trace("object.py")

search_types = ["string", "byte", "word", "dword", "qword"]


def generate_parser(name, parser=None):
    """This is a little bit different from other commands, in that we will
    augment existing commands with new arguments, so we don't always want to
    create a new parser

    TODO: Now that were not doing the reloading stuff we used todo, I wonder if
    we could clean this out the lot, but for now I'm just porting it to close to how it used to work
    """
    if name == "sbobject":
        parser = argparse.ArgumentParser(
            description="""Print the metadata and contents of one or more
                        objects/chunks

Can provide you with a summary of a chunk (one-line) or more verbose information
in multiple lines (e.g. hexdump of the object contents).
You can also list information of multiple chunks, search chunks, etc.
""",
            add_help=False,
            formatter_class=argparse.RawTextHelpFormatter,
            epilog="""E.g.
sbobject mem-0x10 -v -x -M "tag, backtrace"
sbobject mem-0x10 -M "backtrace:5"
Allocated/free flag: M=allocated, F=freed""",
        )

        parser.add_argument(
            "addresses",
            nargs="*",
            default=None,
            help="Address(es) to object(s)/chunk(s) in a memory region associated with a slab",
        )
        group = parser
    else:
        group = parser.add_argument_group("generic optional arguments")

    parser.add_argument(
        "-n",
        dest="name",
        type=str,
        default=None,  # None means search in all slab caches
        help='The cache name (e.g. kmalloc-64). Use "sblist" to get them all',
    )
    group.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help="Use verbose output (multiple for more verbosity)",
    )
    group.add_argument(
        "-h",
        "--help",
        dest="help",
        action="store_true",
        default=False,
        help="Show this help",
    )
    if name == "sbobject":
        group.add_argument(
            "-c",
            "--count",
            dest="count",
            type=h.check_count_value,
            default=1,
            help="""Number of objects/chunks to print linearly (also supports "unlimited"/0
or negative numbers to print objects/chunks going backwards)""",
        )
    group.add_argument(
        "-x",
        "--hexdump",
        dest="hexdump",
        action="store_true",
        default=False,
        help="Hexdump the object/chunk contents",
    )
    group.add_argument(
        "-X",
        dest="hexdump_unit",
        type=h.check_hexdump_unit,
        default=1,
        help=f"Specify hexdump unit ({h.prepare_list(h.hexdump_units)}) when using -x (default: %(default)s)",
    )
    group.add_argument(
        "-m",
        "--maxbytes",
        dest="maxbytes",
        type=h.string_to_int,
        default=0,
        help="Max bytes to dump with -x",
    )
    if name == "sbobject" or name == "sbcache":
        group.add_argument(
            "-N",
            dest="no_newline",
            action="store_true",
            default=False,
            help="Do not output the trailing newline (summary representation)",
        )
    group.add_argument(
        "-p",
        dest="print_offset",
        type=h.string_to_int,
        default=0,
        help="Print data inside at given offset (summary representation)",
    )
    group.add_argument(
        "-M",
        "--metadata",
        dest="metadata",
        type=str,
        default=None,
        help="Comma separated list of metadata to print (previously stored with the 'sbmeta' command)",
    )
    if name == "sbobject" or name == "sbcache":
        group.add_argument(
            "-I",
            "--highlight-types",
            dest="highlight_types",
            type=str,
            default=None,
            help="Comma separated list of chunk types (M, F) for objects/chunks we want to highlight in the output",
        )
    group.add_argument(
        "-H",
        "--highlight-addresses",
        dest="highlight_addresses",
        type=str,
        default=None,
        help="Comma separated list of addresses for objects/chunks we want to highlight in the output",
    )
    group.add_argument(
        "-G",
        "--highlight-metadata",
        dest="highlight_metadata",
        type=str,
        default=None,
        help="""Comma separated list of metadata (previously stored with the 'sbmeta' command)
for objects/chunks we want to highlight in the output""",
    )
    group.add_argument(
        "--highlight-only",
        dest="highlight_only",
        action="store_true",
        default=False,
        help="Only show the highlighted objects/chunks (instead of just '*' them)",
    )
    if name != "sbfree":
        group.add_argument(
            "--use-cache",
            dest="use_cache",
            action="store_true",
            default=False,
            help="""Do not fetch any internal slab data if you know they haven't changed since
last time they were cached""",
        )
    group.add_argument(
        "-s",
        "--search",
        dest="search_value",
        type=str,
        default=None,
        help="Search a value and show match/no match",
    )
    group.add_argument(
        "-S",
        "--search-type",
        dest="search_type",
        type=str,
        default="string",
        help=f"Specify search type ({h.prepare_list(search_types)}) when using -s (default: %(default)s)",
    )
    group.add_argument(
        "--match-only",
        dest="match_only",
        action="store_true",
        default=False,
        help="Only show the matched chunks (instead of just show match/no match)",
    )

    group.add_argument(
        "--depth",
        dest="search_depth",
        type=h.string_to_int,
        default=0,
        help="How far into each chunk to search, starting from chunk header address",
    )
    group.add_argument(
        "--cmds",
        dest="commands",
        type=str,
        default=None,
        help="""Semi-colon separated list of debugger commands to be executed for each chunk that is displayed
('@' is replaced by the chunk address)""",
    )
    group.add_argument(
        "--object-info",
        dest="object_info",
        action="store_true",
        default=False,
        help="Show object info such as its slab/cpu/node/etc. (summary representation)",
    )
    # allows to enable a different log level during development/debugging
    parser.add_argument(
        "--loglevel", dest="loglevel", default=None, help=argparse.SUPPRESS
    )
    # Debug and force printing stuff
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    return parser


def prepare_args_if_negative_count(sb, args):
    """Handle cases where the user wants to print N chunks going backwards.

    We are going to list all the chunks in the memory region associated with
    a slab until we find all the addresses requested and then craft new arguments
    as if the user requested to print from new addresses N chunks before the requested
    addresses before calling parse_objects()
    """

    args.reverse = False
    # Nothing to do if the count is positive or unlimited
    if args.count is None or args.count >= 0:
        return
    # We are making the count positive
    args.count = args.count * -1
    # And we print N chunks before the requested chunk + the actual chunk
    args.count += 1

    addresses = sb.dbg.parse_address(args.addresses)
    if len(addresses) == 0:
        sb.dbg.error("WARNING: No valid address supplied")
        # parser.print_help()
        return

    # We will fill it with new addresses later below
    args.addresses = []

    # In what slab caches to look for objects?
    name = args.name
    if name is not None and name in sb.cache.slab_caches.keys():
        kmem_caches = [sb.cache.slab_caches[name]]
    elif name is None:
        kmem_caches = list(sb.cache.slab_caches.values())

    # Prepare arguments for "sbobject" format
    # i.e. for every address, get the new address N chunks before
    for addr in addresses:
        ret = obj.obj.is_object_address_in_slab_caches(kmem_caches, addr)
        if ret is None and name is not None:
            sb.dbg.error(f"WARNING: Could not find {addr:#x} in slab cache, skipping")
            continue
        (index, objects_list) = ret
        index -= args.count - 1
        if index < 0:
            sb.dbg.error(f"WARNING: Reaching beginning of memory region with {addr:#x}")
            index = 0
        args.addresses.append(f"{objects_list[index].address:#x}")


def parse_arguments(sb, args, ignore_addresses=False):
    log.debug("sbobject.parse_arguments()")
    addresses = []
    if not args.addresses:
        sb.dbg.error("WARNING: No address supplied?")
        # parser.print_help()
        return None
    else:
        if ignore_addresses is False:
            addresses = sb.dbg.parse_address(args.addresses)
            if len(addresses) == 0:
                sb.dbg.error("WARNING: No valid addressses supplied")
                # parser.print_help()
                return None

    if args.hexdump_unit not in h.hexdump_units:
        sb.dbg.error("Wrong hexdump unit specified")
        # parser.print_help()
        return None

    if args.name is not None and args.name not in sb.cache.slab_caches.keys():
        sb.dbg.error(f"Wrong slab cache name specified {args.name}")
        # parser.print_help()
        return None

    if args.search_type not in search_types:
        sb.dbg.error(f"Wrong search type specified {args.search_type}")
        # parser.print_help()
        return None
    if args.search_type != "string" and not args.search_value.startswith("0x"):
        sb.dbg.error("Wrong search value for specified type. Expect 0x-prefixed value")
        # parser.print_help()
        return None

    highlight_addresses = []
    if args.highlight_addresses:
        list_highlight_addresses = [
            e.strip() for e in args.highlight_addresses.split(",")
        ]
        highlight_addresses = sb.dbg.parse_address(list_highlight_addresses)
        if len(highlight_addresses) == 0:
            sb.dbg.error("WARNING: No valid address to highlight supplied")
            # parser.print_help()
            return None
    highlight_metadata = []
    if args.highlight_metadata:
        highlight_metadata = [e.strip() for e in args.highlight_metadata.split(",")]

    # some commands inheriting sbobject arguments don't support highlighting types
    try:
        highlight_types = args.highlight_types
    except AttributeError:
        highlight_types = None
    if highlight_types:
        highlight_types = [e.strip() for e in highlight_types.split(",")]
        for e in highlight_types:
            if e not in ["M", "F"]:
                sb.dbg.error("WARNING: Invalid type to highlight supplied")
                # parser.print_help()
                return None
    else:
        highlight_types = []

    return addresses, highlight_addresses, highlight_metadata, highlight_types


def parse_object_addresses(
    sb,
    addresses,
    opts,
    separate_addresses_non_verbose=True,
    count_printed=None,
):
    """Handle direct sbobject parsing requests that may specify invalid addresses

    :param separate_addresses_non_verbose: False to avoid a separation when printing
                                            one-line chunks, like in freelists
    :param header_once: string to print before printing the first chunk, or None if not needed
    :param count_handle: maximum number of chunks to handle per address, even if not printed, or None if unlimited
    :param count_printed: maximum number of chunks to print in total for all addresses, or None if unlimited.
                            Only useful if handling a freebin.
    :return: the list of objects found
    """
    args = opts.args
    count = args.count

    # In what slab caches to look for objects?
    name = args.name
    if name is not None and name in sb.cache.slab_caches.keys():
        kmem_caches = [sb.cache.slab_caches[name]]
    elif name is None:
        kmem_caches = list(sb.cache.slab_caches.values())
    else:
        print(f"WARN: invalid slab cache name {name} passed to sbobject ")
        return

    all_chunks = []
    chunks = None
    for address in addresses:
        if (
            chunks is not None
            and len(chunks) > 0
            and (separate_addresses_non_verbose or args.verbose > 0)
        ):
            print("-" * 60)

        if count_printed is None:
            count_linear = count
        elif count is None:
            count_linear = count_printed
        else:
            count_linear = min(count_printed, count)

            print(f"WARN: {address:#x} not found in slab caches")
            return
        ret = obj.obj.is_object_address_in_slab_caches(kmem_caches, address)
        if ret is None:
            return
        (index, objects_list) = ret

        chunks = parse_object_list(
            objects_list,
            index,
            sb,
            count_linear,
            opts.count_handle,
            args.search_depth,
            args.hexdump_unit,
            args.search_value,
            args.search_type,
            args.match_only,
            args.print_offset,
            args.verbose,
            args.no_newline,
            args.debug,
            args.hexdump,
            args.maxbytes,
            args.metadata,
            highlight_types=opts.highlight_types,
            highlight_addresses=opts.highlight_addresses,
            highlight_metadata=opts.highlight_metadata,
            highlight_only=args.highlight_only,
            header_once=opts.header_once,
            commands=args.commands,
            use_cache=opts.use_cache,
            name=args.name,
            is_region=opts.is_region,
            is_freelist=opts.is_freelist,
            object_info=args.object_info,
        )
        if chunks is not None and len(chunks) > 0:
            all_chunks.extend(chunks)
            if count_printed is not None:
                count_printed -= len(chunks)
        if count_printed == 0:
            break
    return all_chunks


def parse_object_list(
    objects_list,
    index,
    sb,
    count=1,
    count_handle=None,
    search_depth=0,
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
    header_once=None,
    commands=None,
    use_cache=False,
    name=None,
    indent="",
    is_region=False,
    is_freelist=False,
    object_info=False,
):
    """Parse many slab objects starting from a given address and print their info

    :param objects_list: list of objects (linear view for memory regions or freelist)
    :param index: index in objects_list[] to start parsing from
    :param sb: slab object (libslub constants and helpers)
    :param count: see sbobject's ArgumentParser definition
                    maximum number of chunks to print, or None if unlimited
    :param count_handle: maximum number of chunks to handle per address, even if not printed, or None if unlimited
    :param search_depth: see sbobject's ArgumentParser definition
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
    :param header_once: string to print before printing the first chunk, or None if not needed
    :param commands: see sbobject's ArgumentParser definition
    :param use_cache: see sbobject's ArgumentParser definition
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
    dump_offset = 0
    while True:
        prefix = ""  # used for one-line output
        suffix = ""  # used for one-line output
        epilog = ""  # used for verbose output

        if object_info:
            show_slab_cache = name is None
            suffix += f" ({o.info(show_slab_cache=show_slab_cache)})"

        colorize_func = str  # do not colorize by default
        if metadata is not None:
            list_metadata = [e.strip() for e in metadata.split(",")]
            L, s, e, colorize_func = meta.get_metadata(
                o.address, list_metadata=list_metadata
            )
            suffix += s
            epilog += e
            o.metadata = L  # save so we can easily export to json later

        if search_value is not None:
            if not libslub.debugger.search_chunk(
                sb.dbg,
                o.address,
                o.size,
                search_value,
                search_type=search_type,
                depth=search_depth,
            ):
                found_match = False
                suffix += " [NO MATCH]"
            else:
                suffix += pu.light_green(" [MATCH]")
                found_match = True

        # NOTE: We use this for exploiting Cisco ASA heap bug, and it just
        # kind of inherited into all of the libraries we built. Arguably it is useful but it should be revisited to
        # be way more powerful, as is very very specific at the moment
        if print_offset != 0:
            mem = sb.dbg.read_memory(o.address + print_offset, 4)
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
            elif index == count_objects - 1:
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
            if (o.inuse is True and "M" in highlight_types) or (
                o.inuse is False and "F" in highlight_types
            ):
                found_highlight = True
            if len(highlight_metadata) > 0:
                # We retrieve all metadata since we want to highlight chunks containing any of the
                # metadata, even if we don't show some of the metadata
                _, s, _, _ = meta.get_metadata(o.address, list_metadata="all")
                for m in highlight_metadata:
                    # we check in the one-line output as it should have less non-useful information
                    if m in s:
                        found_highlight = True
                        highlight_metadata_found.add(m)
            if found_highlight:
                prefix += "* "
            if (not highlight_only or found_highlight) and (
                not match_only or found_match
            ):
                if header_once is not None:
                    print(indent + header_once)
                    header_once = None
                if no_newline:
                    print(
                        indent
                        + prefix
                        + o.to_string(colorize_func=colorize_func)
                        + suffix,
                        end="",
                    )
                else:
                    print(
                        indent
                        + prefix
                        + o.to_string(colorize_func=colorize_func)
                        + suffix
                    )
                printed = True
        elif verbose >= 1 and (not match_only or found_match):
            if header_once is not None:
                print(indent + header_once)
                header_once = None
            print(indent + o.to_string(colorize_func=colorize_func))
            printed = True
        if printed:
            if hexdump:
                h.print_hexdump_chunk(
                    sb,
                    o,
                    maxlen=maxbytes,
                    off=dump_offset,
                    unit=hexdump_unit,
                    verbose=verbose,
                )
            if verbose >= 1 and epilog:
                print(indent + epilog, end="")
            if commands:
                for command in commands.split(";"):
                    formatted_command = command.replace("@", f"{o.address:#x}")
                    if no_newline:
                        print(indent + sb.dbg.execute(formatted_command), end="")
                    else:
                        print(indent + sb.dbg.execute(formatted_command))
            chunks.append(o)
            if count is not None:
                count -= 1
        if count_handle is not None:
            count_handle -= 1
        index += 1
        if count != 0 and count_handle != 0:
            if printed and (verbose >= 1 or hexdump):
                print(indent + "--")
            if index == count_objects:
                # Only print the chunk type for non verbose
                print("Stopping due to end of memory region")
                break
            o = objects_list[index]
        else:
            break

    # XXX - can't really show that atm as we have lots of memory regions
    # each associated with a given slab, so would spam messages
    # if len(highlight_addresses) != 0:
    #    pu.print_error("WARNING: Could not find these chunk addresses: %s" % (", ".join(["0x%x" % x for x in highlight_addresses])))
    # if len(highlight_metadata-highlight_metadata_found) != 0:
    #    pu.print_error("WARNING: Could not find these metadata: %s" % (", ".join(list(highlight_metadata-highlight_metadata_found))))

    return chunks


def slub_object(
    sb,
    args,
):
    """Dump information about a given object

    This is the main function accessed via gdb commands like sboject, etc"""

    sb.cache.update_all(
        name=args.name,
        show_status=args.debug,
        use_cache=args.use_cache,
    )

    log.debug("slub_object()")

    prepare_args_if_negative_count(sb, args)

    ret = parse_arguments(sb, args)
    if ret is None:
        return
    addresses, highlight_addresses, highlight_metadata, highlight_types = ret

    print_object_options = {
        "highlight_addresses": highlight_addresses,
        "highlight_metadata": highlight_metadata,
        "highlight_types": highlight_types,
        "use_cache": True,
        "is_region": True,
        "main_slab_free_list": None,
        "count_handle": None,
        "is_freelist": False,
        "header_once": None,
    }
    # TODO: Really we should just get rid of args, but this is for porting speed
    # Presumably there's also an easier way without **...
    opts = Options(**{"args": Options(**vars(args)), **print_object_options})
    # we enforced updating the cache once above so no need to do it for every
    # chunk
    parse_object_addresses(sb, addresses, opts)
