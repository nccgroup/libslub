import argparse
import logging

log = logging.getLogger("libslub")
log.trace("sbtrace.py")

# TODO: Code from this, trace, and break can likely all be merged


def generate_parser():
    parser = argparse.ArgumentParser(
        description="""Start/stop watching full-slabs for a slab cache

Setup break points for the specified slab names

It is recommended to enable it when analyzing objects allocated/freed.

This is required in order to be able to list objects allocated in full slabs
since otherwise the SLUB allocator won't know them until they are not in a
full-slabs anymore""",
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-h",
        "--help",
        dest="help",
        action="store_true",
        default=False,
        help="Show this help",
    )
    # allows to enable a different log level during development/debugging
    parser.add_argument(
        "--loglevel", dest="loglevel", default=None, help=argparse.SUPPRESS
    )

    parser.add_argument(
        "names", nargs="*", default=[], type=str, help="Slab names (e.g. 'kmalloc-1k')"
    )
    return parser


def slub_watch(
    sb,
    args,
):
    """Command to start/stop watching full-slabs for a slab cache"""
    if not sb.breakpoints_enabled:
        print("WARNING: breakpoints are not enabled. Nothing to do.")
        return
    if not sb.breakpoints.supported:
        print("WARN: breakpoint functions won't work, unsupported kernel version")
        return

    # TODO: Probably check we have breakpoints of find for this kernel version?
    for name in args.names:
        slab_cache = sb.find_slab_cache(name)
        if slab_cache is None:
            print("Slab cache '%s' not found" % name)
            return

        if name in sb.watch_caches:
            print("Stopped watching slab cache '%s'" % name)
            sb.watch_caches.remove(name)
        else:
            print("Started watching slab cache '%s'" % name)
            sb.watch_caches.append(name)
        sb.breakpoints.update_breakpoints()
