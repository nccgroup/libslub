import argparse
import pickle
import pprint

import libslub.frontend.printutils as pu

meta_cache = {}
backtrace_ignore = set([])

colorize_table = {
    "red": pu.red,
    "green": pu.green,
    "yellow": pu.yellow,
    "blue": pu.blue,
    "purple": pu.purple,
    "cyan": pu.cyan,
    "gray": pu.gray,
    "lightred": pu.light_red,
    "lightgreen": pu.light_green,
    "lightyellow": pu.light_yellow,
    "lightblue": pu.light_blue,
    "lightpurple": pu.light_purple,
    "lightcyan": pu.light_cyan,
    "lightgray": pu.light_gray,
    "white": pu.white,
    "black": pu.black,
}

# TODO: This may want to go in a pwndbg specific cache directory vs cwd
METADATA_DB = "metadata.pickle"

config_options = {
    "ignore": {
        "backtrace": "Skip printing the given functions in back trace output",
    },
}


def save_metadata_to_file(filename):
    """During development, we reload libslub and lose the metadata database
    so this allows saving it easily into a file before doing so
    """
    d = {}
    d["meta_cache"] = meta_cache
    d["backtrace_ignore"] = backtrace_ignore
    pickle.dump(d, open(filename, "wb"))


def load_metadata_from_file(filename):
    """During development, we reload libslub and lose the metadata database
    so this allows reloading it easily from a file
    """
    global meta_cache, backtrace_ignore
    d = pickle.load(open(filename, "rb"))
    meta_cache = d["meta_cache"]
    backtrace_ignore = d["backtrace_ignore"]


def get_metadata(address, list_metadata=[]):
    """
    :param address: the address to retrieve metatada from
    :param list_metadata: If a list, the list of metadata to retrieve (even empty list).
                          If the "all" string, means to retrieve all metadata
    :return: the following L, suffix, epilog, colorize_func
    """

    L = []  # used for json output
    suffix = ""  # used for one-line output
    epilog = ""  # used for verbose output
    colorize_func = str  # do not colorize by default

    if address not in meta_cache:
        epilog += "chunk address not found in metadata database\n"
        return None, suffix, epilog, colorize_func

    # This allows calling get_metadata() by not specifying any metadata
    # but meaning we want to retrieve them all
    if list_metadata == "all":
        list_metadata = list(meta_cache[address].keys())
        if "backtrace" in list_metadata:
            # enforce retrieving all the functions from the backtrace
            list_metadata.remove("backtrace")
            list_metadata.append("backtrace:-1")

    opened = False
    for key in list_metadata:
        param = None
        if ":" in key:
            key, param = key.split(":")
        if key not in meta_cache[address]:
            if key != "color":
                suffix += " | N/A"
                epilog += "'%s' key not found in metadata database\n" % key
                opened = True
                L.append(None)
            continue
        if key == "backtrace":
            if param is None:
                funcs_list = get_first_function(address)
            else:
                funcs_list = get_functions(address, max_len=int(param))
            if funcs_list is None:
                suffix += " | N/A"
            elif len(funcs_list) == 0:
                # XXX - atm if we failed to parse the functions from the debugger
                # we will also show "filtered" even if it is not the case
                suffix += " | filtered"
            else:
                suffix += " | %s" % ",".join(funcs_list)
            epilog += "%s" % meta_cache[address]["backtrace"]["raw"]
            L.append(funcs_list)
            opened = True
        elif key == "color":
            color = meta_cache[address][key]
            colorize_func = colorize_table[color]
        else:
            suffix += " | %s" % meta_cache[address][key]
            epilog += "%s\n" % meta_cache[address][key]
            L.append(meta_cache[address][key])
            opened = True
    if opened:
        suffix += " |"

    return L, suffix, epilog, colorize_func


def get_first_function(address):
    return get_functions(address, max_len=1)


def get_functions(address, max_len=None):
    L = []
    if address not in meta_cache:
        return None
    if "backtrace" not in meta_cache[address]:
        return None
    funcs = meta_cache[address]["backtrace"]["funcs"]
    for f in funcs:
        if f in backtrace_ignore:
            continue
        L.append(f)
        if max_len is not None and len(L) == max_len:
            break
    return L


def list_metadata(args, address):
    """Show the metadata database for all addresses or a given address

    if verbose == 0, shows single-line entries (no "backtrace" if not requested)
    if verbose == 1, shows single-line entries (all keys)
    if verbose == 2, shows multi-line entries (no "backtrace" if not requested)
    if verbose == 3, shows multi-line entries (all keys)
    """

    if len(meta_cache) != 0:
        pu.print_header("Metadata database", end=None)

        if args.metadata is None:
            # if no metadata provided by user, we get them all
            list_metadata = []
            for k, d in meta_cache.items():
                for k2, d2 in d.items():
                    if k2 not in list_metadata:
                        list_metadata.append(k2)
            if args.verbose == 0 and "backtrace" in list_metadata:
                list_metadata.remove("backtrace")
        else:
            list_metadata = [e.strip() for e in args.metadata.split(",")]

        if args.verbose <= 1:
            print("| address | ", end="")
            print(" | ".join(list_metadata), end="")
            print(" |")
            for k, d in meta_cache.items():
                if address is None or k == address:
                    L, s, e, colorize_func = get_metadata(
                        k, list_metadata=list_metadata
                    )
                    addr = colorize_func(f"0x{k:x}")
                    print(f"| {addr}", end="")
                    print(s)
        else:
            for k, d in meta_cache.items():
                if address is None or k == address:
                    L, s, e, colorize_func = get_metadata(
                        k, list_metadata=list_metadata
                    )
                    addr = colorize_func(f"0x{k:x}")
                    print(f"{addr}:")
                    print(e)
    else:
        pu.print_header("Metadata database", end=None)
        print("N/A")

    print("")

    if len(backtrace_ignore) != 0:
        pu.print_header("Function ignore list for backtraces", end=None)
        pprint.pprint(backtrace_ignore)
    else:
        pu.print_header("Function ignore list for backtraces", end=None)
        print("N/A")


def get_supported_metadata():
    """Print the supported metadata keys and their description"""
    s = "Supported metadata keys:\n"
    for k, d in config_options.items():
        s += f"  {k}:\n"
        for k2, d2 in d.items():
            s += f"    {k2}: {d2}\n"
    return s


def configure_metadata(args, feature, key, values):
    """Save given metadata (key, values) for a given feature (e.g. "backtrace")

    :param feature: name of the feature (e.g. "ignore")
    :param key: name of the metadata (e.g. "backtrace")
    :param values: list of values to associate to the key
    """

    if args.verbose >= 1:
        print("Configuring metadata database...")
    if key == "backtrace":
        if feature == "ignore":
            backtrace_ignore.update(values)
        else:
            pu.print_error("WARNING: Unsupported feature")
            pu.print_error(get_supported_metadata())
            return
    else:
        pu.print_error("WARNING: Unsupported key")
        pu.print_error(get_supported_metadata())
        return


def delete_metadata(args, address):
    """Delete metadata for a given chunk's address"""

    if address not in meta_cache:
        return

    if args.verbose >= 1:
        print(f"Deleting metadata for {address} from database...")
    del meta_cache[address]


def add_metadata(sb, args, address, key, value, append=False):
    """Save given metadata (key, value) for a given chunk's address
    E.g. key = "tag" and value is an associated user-defined tag
    """

    if args.verbose >= 1:
        print("Adding to metadata database...")
    if key == "backtrace":
        result = sb.dbg.get_backtrace()
    elif key == "color":
        if value not in colorize_table:
            sb.dbg.error(
                f"ERROR: Unsupported color. Need one of: {', '.join(colorize_table.keys())}"
            )
            return
        result = value
    else:
        result = value

    if address not in meta_cache:
        meta_cache[address] = {}
    if key != "backtrace" and key != "color":
        if append is True and key in meta_cache[address].keys():
            result = meta_cache[address][key] + " ; " + result
    meta_cache[address][key] = result


def generate_parser():
    """Generate a parser for the metadata database"""

    parser = argparse.ArgumentParser(
        description="""Handle metadata associated with object/chunk addresses""",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
        epilog="""NOTE: use 'sbmeta <action> -h' to get more usage info""",
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
        help="""Save metadata for a given chunk address""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""The saved metadata can then be shown in any other commands like
'sbcache', etc.

E.g.
  sbmeta add mem-0x10 tag "service_user struct"
  sbmeta add 0xdead0030 color green
  sbmeta add 0xdead0030 backtrace""",
    )
    add_parser.add_argument("address", help="Address to link the metadata to")
    add_parser.add_argument(
        "key",
        help='Key name of the metadata (e.g. "backtrace", "color", "tag" or any name)',
    )
    add_parser.add_argument(
        "value",
        nargs="?",
        help='Value of the metadata, associated with the key (required except when adding a "backtrace")',
    )
    add_parser.add_argument(
        "--append",
        dest="append",
        action="store_true",
        help="Append value if the key/value already exist instead of overwriting previous value",
    )

    del_parser = actions.add_parser(
        "del",
        help="""Delete metadata associated with a given chunk address""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""E.g.
sbmeta del mem-0x10
sbmeta del 0xdead0030""",
    )
    del_parser.add_argument("address", help="Address to remove the metadata for")

    list_parser = actions.add_parser(
        "list",
        help="""List metadata for a chunk address or all chunk addresses (debugging)""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""E.g.
sbmeta list mem-0x10
sbmeta list 0xdead0030 -M backtrace
sbmeta list
sbmeta list -vvvv
sbmeta list -M "tag, backtrace:3""",
    )
    list_parser.add_argument(
        "address", nargs="?", help="Address to remove the metadata for"
    )
    list_parser.add_argument(
        "-M",
        "--metadata",
        dest="metadata",
        type=str,
        default=None,
        help="Comma separated list of metadata to print",
    )

    config_parser = actions.add_parser(
        "config",
        help="Configure general metadata behaviour",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""E.g.
sbmeta config ignore backtrace _nl_make_l10nflist __GI___libc_free""",
    )
    config_parser.add_argument("feature", help='Feature to configure (e.g. "ignore")')
    config_parser.add_argument(
        "key", help='Key name of the metadata (e.g. "backtrace")'
    )
    config_parser.add_argument(
        "values",
        nargs="+",
        help="Values of the metadata, associated with the key (e.g. list of function to ignore in a backtrace)",
    )

    # Add supported keys to config_parser epilogue
    config_parser.epilog += f"\n\n{get_supported_metadata()}"

    # allows to enable a different log level during development/debugging
    parser.add_argument(
        "--loglevel", dest="loglevel", default=None, help=argparse.SUPPRESS
    )
    # allows to save metadata to file during development/debugging
    parser.add_argument(
        "-S",
        "--save-db",
        dest="save",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    # allows to load metadata from file during development/debugging
    parser.add_argument(
        "-L",
        "--load-db",
        dest="load",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    return parser


def slub_meta(sb, args):
    if args.action is None and not args.save and not args.load:
        sb.dbg.error("Dumping metadata requires an action")
        generate_parser().print_help()
        return

    if args.action == "list" or args.action == "add" or args.action == "del":
        address = None
        if args.address is not None:
            addresses = sb.dbg.parse_address(args.address)
            if len(addresses) == 0:
                sb.dbg.error("Invalid address supplied")
                generate_parser().print_help()
                return
            address = addresses[0]

    if args.action == "list":
        list_metadata(args, address)
        return

    if args.action == "del":
        delete_metadata(args, address)
        return

    if args.action == "config":
        configure_metadata(args, args.feature, args.key, args.values)
        return

    if args.action == "add":
        add_metadata(sb, args, address, args.key, args.value, args.append)
        return

    if args.save:
        if args.verbose >= 0:  # always print since debugging feature
            print("Saving metadata database to file...")
        # TODO: Maybe this file should be configurable
        save_metadata_to_file(METADATA_DB)
        return

    if args.load:
        if args.verbose >= 0:  # always print since debugging feature
            print("Loading metadata database from file...")
        load_metadata_from_file(METADATA_DB)
        return
