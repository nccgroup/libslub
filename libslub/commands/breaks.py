import argparse
import logging

# NOTE: break is a reserved keyword and python, thus the weird name despite slub_break
log = logging.getLogger("libslub")
log.trace("breaks.py")


def generate_parser():
    parser = argparse.ArgumentParser(
        description="""Start/stop breaking on object allocations for a slab cache

Setup break points for the specified slab names""",
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


def slub_break(
    sb,
    args,
):
    """Command to start/stop breaking on object allocations for a slab cache"""
    if not sb.breakpoints_enabled:
        print("WARNING: breakpoints are not enabled. Nothing to do.")
        return
    if not sb.breakpoints.supported:
        print("WARN: breakpoint functions won't work, unsupported kernel version")
        return

    if len(args.names) == 0:
        print("No slab cache names specified")
        return

    for name in args.names:
        slab_cache = sb.find_slab_cache(name)
        if slab_cache is None:
            print("Slab cache '%s' not found" % name)
            return

        if name in sb.break_caches:
            print("Stopped breaking slab cache '%s'" % name)
            sb.break_caches.remove(name)
        else:
            print("Started breaking slab cache '%s'" % name)
            sb.break_caches.append(name)
        sb.breakpoints.update_breakpoints()
