import argparse
import logging
import pickle

log = logging.getLogger("libslub")
log.trace("sbslabdb.py")

# The actual database of slabs and associated chunk addresses
# that are tracked as part of the "add" and "del" commands
slab_db = {}

# just a cache to avoid querying structure in memory each time
# but we will query it again if the address we "add" or "delete"
# is not there
cached_info = {}

SLAB_DB = "slabdb.pickle"


def save_slab_db_to_file(filename):
    """During development, we reload libslub and lose the slab database
    so this allows saving it easily into a file before doing so
    """
    d = {}
    d["slab_db"] = slab_db
    pickle.dump(d, open(filename, "wb"))


def load_slab_db_from_file(filename):
    """During development, we reload libslub and lose the slab database
    so this allows reloading it easily from a file
    """
    global slab_db
    d = pickle.load(open(filename, "rb"))
    slab_db = d["slab_db"]


def generate_parser():
    parser = argparse.ArgumentParser(
        description="""Handle saving slab addresses associated with object/chunk addresses""",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
        epilog="""This is particularly useful to be able to track full slabs

NOTE: use 'sbslabdb <action> -h' to get more usage info""",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help="Use verbose output (multiple for more verbosity)",
    )
    parser.add_argument(
        "-h",
        "--help",
        dest="help",
        action="store_true",
        default=False,
        help="Show this help",
    )

    actions = parser.add_subparsers(help="Action to perform", dest="action")

    add_parser = actions.add_parser(
        "add",
        help="""Add slab address to the list""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""XXX""",
    )
    add_parser.add_argument("cache", help='slab cache (e.g. "kmalloc-1k")')

    add_parser.add_argument("address", help="Chunk address to add")

    del_parser = actions.add_parser(
        "del",
        help="""Delete slab address from the list""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""XXX""",
    )
    del_parser.add_argument("cache", help='slab cache (e.g. "kmalloc-1k")')
    del_parser.add_argument("address", help="Chunk address to remove")

    actions.add_parser(
        "list",
        help="""List all the slab addresses from the list (debugging)""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""XXX""",
    )

    # allows to enable a different log level during development/debugging
    parser.add_argument(
        "--loglevel", dest="loglevel", default=None, help=argparse.SUPPRESS
    )
    # allows to save the slab db to file during development/debugging
    parser.add_argument(
        "-S",
        "--save-db",
        dest="save",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    # allows to load the slab db from file during development/debugging
    parser.add_argument(
        "-L",
        "--load-db",
        dest="load",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    return parser


def get_slab_address(sb, args, chunk_addr, cache_name):
    global cached_info

    # Check our local cache first
    log.debug("Checking")
    if cache_name in cached_info.keys():
        for page_addr, (region_start, region_end) in cached_info[cache_name].items():
            if chunk_addr >= region_start and chunk_addr < region_end:
                return page_addr

    # Not found in our cache, so query structures and memory to update our cache
    log.debug("Updating cache")
    cached_info[cache_name] = sb.get_slab_cache_memory_pages_ranges(
        name=args.cache, dict_enabled=True
    )

    # And check again
    log.debug("Checking again")
    for page_addr, (region_start, region_end) in cached_info[cache_name].items():
        if chunk_addr >= region_start and chunk_addr < region_end:
            return page_addr

    log.debug("Not found")
    return None


def slub_db(sb, args):
    if args.action is None and not args.save and not args.load:
        sb.dbg.error("Database usage requires an action")
        generate_parser().print_help()
        return

    if args.action == "list":
        for cache_name, d in slab_db.items():
            print(f"slab cache: {cache_name}")
            for slab_addr, L in d.items():
                print(f"\tslab @ {slab_addr:#x}")
                for addr in L:
                    print(f"\t\t- {addr:#x}")
        return

    if args.save:
        if args.verbose >= 0:  # always print since debugging feature
            print("Saving slabs database to file...")
        save_slab_db_to_file(SLAB_DB)
        return

    if args.load:
        if args.verbose >= 0:  # always print since debugging feature
            print("Loading slabs database from file...")
        load_slab_db_from_file(SLAB_DB)
        return

    address = None
    if args.address is not None:
        addresses = sb.dbg.parse_address(args.address)
        if len(addresses) == 0:
            sb.dbg.error("WARNING: No valid address supplied")
            generate_parser().print_help()
            return
        address = addresses[0]

    if not args.cache:
        sb.dbg.error("WARNING: No valid cache name supplied")
        generate_parser().print_help()
        return

    if args.action == "del":
        if args.cache not in slab_db.keys():
            log.debug(f"Warning: tried to remove from non-tracked cache: {args.cache}")
            return
        slab_addr = get_slab_address(sb, args, address, args.cache)
        if not slab_addr:
            log.debug(
                f"Warning: tried to remove chunk address: {address:#x} from non-existing slab in cache: {args.cache}"
            )
            return
        if slab_addr not in slab_db[args.cache].keys():
            log.debug(
                f"Warning: tried to remove chunk address: {address:#x} from non-tracked slab in cache: {args.cache}"
            )
            return
        if address not in slab_db[args.cache][slab_addr]:
            log.debug(
                f"Warning: tried to remove non-existing chunk address: {address:#x} from slab address: {slab_addr:#x} in cache: {args.cache}"
            )
            return
        slab_db[args.cache][slab_addr].remove(address)
        if len(slab_db[args.cache][slab_addr]) == 0:
            del slab_db[args.cache][slab_addr]
        return

    if args.action == "add":
        if args.cache not in slab_db.keys():
            slab_db[args.cache] = {}
        slab_addr = get_slab_address(sb, args, address, args.cache)
        if not slab_addr:
            log.debug(
                f"Warning: tried to add chunk address: {address:#x} from non-existing slab in cache: {args.cache}"
            )
            return
        if slab_addr not in slab_db[args.cache].keys():
            slab_db[args.cache][slab_addr] = set([])
        if address in slab_db[args.cache][slab_addr]:
            log.debug(
                f"Warning: tried to add existing chunk address: {address:#x} to slab @ {slab_addr:#x} and cache: {args.cache}"
            )
        else:
            slab_db[args.cache][slab_addr].add(address)
        return
