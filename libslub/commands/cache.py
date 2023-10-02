import argparse
import logging

import libslub.commands.object as cmd_object
import libslub.frontend.helpers as h
from libslub.frontend.helpers import Options

log = logging.getLogger("libslub")
log.trace("cache.py")


def generate_parser():
    parser = argparse.ArgumentParser(
        description="""Print the metadata and contents of one or all slab cache(s)

If you don't specify any slab cache name, it will print all of them but it will take some time to parse structures in memory""",
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # "sbobject" also has this argument but default for
    # "sbcache" is to show unlimited number of chunks
    parser.add_argument(
        "-c",
        "--count",
        dest="count",
        type=h.check_count_value_positive,
        default=None,
        help="""Number of chunks to print linearly in each slab or in each freelist""",
    )
    # XXX - is it a feature we want for filtering too?
    # parser.add_argument(
    #    "-C", "--count-slab", dest="count_slab", type=h.check_count_value_positive, default=None,
    #    help="""Number of slabs to print for each cpu"""
    # )
    parser.add_argument(
        "--cpu",
        dest="cpu",
        type=int,
        default=None,
        help="""Show CPU specified only, instead of all slabs (Ignore node's partial slabs and full slabs)""",
    )
    parser.add_argument(
        "--main-slab",
        dest="main_slab",
        action="store_true",
        default=None,
        help="""Show main slabs for CPUs only, instead of all slabs (Ignore CPU partial slabs, node's partial slabs and full slabs)""",
    )
    parser.add_argument(
        "--partial-slab",
        dest="partial_slab",
        action="store_true",
        default=None,
        help="""Show partial slabs for CPUs only, instead of all slabs (Ignore CPU main slabs, node's partial slabs and full slabs)""",
    )
    parser.add_argument(
        "--node-slab",
        dest="node_slab",
        action="store_true",
        default=None,
        help="""Show partial slabs for nodes only, instead of all slabs (Ignore CPU main/partial slabs and node's full slabs)""",
    )
    parser.add_argument(
        "--full-slab",
        dest="full_slab",
        action="store_true",
        default=None,
        help="""Show full slabs only, instead of all slabs (Ignore CPU main and partial slabs, node's partial slabs)""",
    )
    parser.add_argument(
        "--show-freelist",
        dest="show_freelist",
        action="store_true",
        default=None,
        help="""Show the freelists for each slab (not shown by default)""",
    )
    parser.add_argument(
        "--show-lockless-freelist",
        dest="show_lockless_freelist",
        action="store_true",
        default=None,
        help="""Show the freelist associated to a CPU for the main slab (not shown by default)""",
    )
    parser.add_argument(
        "--show-region",
        dest="show_region",
        action="store_true",
        default=None,
        help="""Show the objects in the memory region for each slab (not shown by default)""",
    )
    parser.add_argument(
        "--hide-title",
        dest="hide_title",
        action="store_true",
        default=False,
        help="""Hide the "region:" or "freelist:" titles (shown by default) when showing regions or freelists""",
    )
    parser.add_argument(
        "--object-only",
        dest="object_only",
        action="store_true",
        default=None,
        help="""Do not show structures' fields and show objects only (still requires --show-freelist and/or --show-region)""",
    )
    # other arguments are implemented in the "sbobject" command
    # and will be shown after the above

    return cmd_object.generate_parser("sbcache", parser)


def slub_cache(
    sb,
    args,
):
    """"""
    sb.cache.update_all(
        name=args.name,
        show_status=args.debug,
        use_cache=args.use_cache,
    )
    args.use_cache = True  # we can use the cache from now on

    log.debug("slub_cache()")
    # Prepare fake arguments for "sbobject" format
    args.addresses = ["0x0"]
    # won't use it until we parse actual memory regions
    # where we will parse cached memory regions directly at that time anyway
    ret = cmd_object.parse_arguments(sb, args, ignore_addresses=True)
    if ret is None:
        return
    (
        addresses,
        highlight_addresses,
        highlight_metadata,
        highlight_types,
    ) = ret

    # this is not a real user argument but is used internally to know if we need to print stuff
    output_filtered = False
    cpu_filtered = False
    if (
        args.main_slab is True
        or args.partial_slab is True
        or args.node_slab is True
        or args.full_slab is True
    ):
        output_filtered = True
    if args.cpu is not None:
        cpu_filtered = True
    if (
        args.cpu is not None
        and (args.node_slab is True or args.full_slab is True)
        and args.main_slab is not True
        and args.partial_slab is not True
    ):
        print("WARNING: --cpu will be ignored")

    name = args.name

    extra = {
        "highlight_addresses": highlight_addresses,
        "highlight_metadata": highlight_metadata,
        "highlight_types": highlight_types,
        "output_filtered": output_filtered,
        "cpu_filtered": cpu_filtered,
    }
    # TODO: Really we should just get rid of args, but this is for porting speed
    # Presumably there's also an easier way without **...
    opts = Options(**{"args": Options(**vars(args)), **extra})

    if name is not None and name in sb.cache.slab_caches.keys():
        sb.cache.slab_caches[name].print(cmd=opts)
    elif name is None:
        for name, kmem_cache in sb.cache.slab_caches.items():
            kmem_cache.print(cmd=opts)
    return
