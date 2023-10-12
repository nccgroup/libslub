import argparse
import logging

import gdb

log = logging.getLogger("libslub")
log.trace("list.py")


def generate_parser():
    parser = argparse.ArgumentParser(
        description="""Show information about all the slab caches on the system

Equivalent to "cat /proc/slabinfo" in userland.""",
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
        "-p",
        dest="pattern",
        default=None,
        help="Only show caches that contain that pattern",
    )
    parser.add_argument(
        "-k",
        dest="kmalloc",
        default=False,
        action="store_true",
        help="Only show most usual caches (kmalloc-8, ... kmalloc-8k)",
    )
    return parser


def slub_list(sb, args):
    """List the slub caches on the system.

    Equivalent to "cat /proc/slabinfo" in userland. Called by command handlers
    in stand alone script to or external framework like pwndbg.

    gdb: sblist
    pwndbg: slublist
    """

    # TODO: These needs to be abstracted away from gdb
    page_type = gdb.lookup_type("struct page")

    print(
        "name                    objs inuse slabs size obj_size objs_per_slab pages_per_slab"
    )

    # Each slab_cache is a dictionary matching the kmem_cache structure of the current slab cache
    # struct kmem_cache {: https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L90
    for slab_cache in sb.iter_slab_caches():
        name = slab_cache["name"].string()  # Name (only for display!)

        # skip if don't want to see them all
        if args.pattern and args.pattern not in name:
            continue
        if args.kmalloc and name not in sb.sb.kmalloc_caches:
            continue

        size = int(slab_cache["size"])  # The size of an object including metadata
        obj_size = int(
            slab_cache["object_size"]
        )  # The size of an object without metadata
        cnt_objs, cnt_inuse, cnt_slabs = 0, 0, 0

        # Get the gdb.Value representing the current kmem_cache_cpu
        cpu_cache = sb.get_current_slab_cache_cpu(slab_cache)

        # kmem_cache_cpu->page == The slab from which we are allocating
        # struct page {:
        # https://elixir.bootlin.com/linux/v5.15/source/include/linux/mm_types.h#L70
        try:
            cpu_cache["page"]
            slab_struct_name = "page"
        except Exception:
            try:
                cpu_cache["slab"]
                slab_struct_name = "slab"
            except Exception:
                raise Exception(
                    "Could not find the slab structure in kmem_cache_cpu. File a bug."
                )
        if cpu_cache[slab_struct_name]:
            cnt_objs = cnt_inuse = (
                int(cpu_cache[slab_struct_name]["objects"]) & sb.UNSIGNED_INT
            )
            # kmem_cache_cpu->freelist == Pointer to next available object
            if cpu_cache["freelist"]:
                cnt_inuse -= len(
                    list(sb.walk_freelist(slab_cache, cpu_cache["freelist"]))
                )
            cnt_slabs += 1

        # kmem_cache_cpu->partial == Partially allocated frozen slabs
        # struct page {: https://elixir.bootlin.com/linux/v5.15/source/include/linux/mm_types.h#L70
        if cpu_cache["partial"]:
            slab = cpu_cache["partial"]
            while slab:
                cnt_objs += (
                    int(slab["objects"]) & sb.UNSIGNED_INT
                )  # number of chunks in that slab
                cnt_inuse += (
                    int(slab["inuse"]) & sb.UNSIGNED_INT
                )  # number of allocated chunks in that slab
                cnt_slabs += 1
                slab = slab.dereference()["next"]  # next partial slab

        # kmem_cache->node == The slab lists for all objects
        # struct kmem_cache_node {: https://elixir.bootlin.com/linux/v5.15/source/mm/slab.h#L533
        node_cache = slab_cache["node"].dereference().dereference()
        for slab in sb.for_each_entry(page_type, node_cache["partial"], "lru"):
            cnt_objs += int(slab["objects"]) & sb.UNSIGNED_INT
            cnt_inuse += int(slab["inuse"]) & sb.UNSIGNED_INT
            cnt_slabs += 1

        # Word size structure that can be atomically updated or read and that
        # contains both the order and the number of objects that a slab of the
        # given order would contain.
        # struct kmem_cache_order_objects {: https://elixir.bootlin.com/linux/v5.15/source/include/linux/slub_def.h#L83
        oo = slab_cache["oo"]["x"]
        # https://elixir.bootlin.com/linux/v5.15/source/mm/slub.c#L412 and https://elixir.bootlin.com/linux/v5.15/source/mm/slub.c#L252
        objs_per_slab = oo & ((1 << 16) - 1)
        # https://elixir.bootlin.com/linux/v5.15/source/mm/slub.c#L407 and https://elixir.bootlin.com/linux/v5.15/source/mm/slub.c#L251
        pages_per_slab = 2 ** (oo >> 16)

        print(
            "%-23s %4d %5d %5d %4d %8d %13d %14d"
            % (
                name,
                cnt_objs,
                cnt_inuse,
                cnt_slabs,
                size,
                obj_size,
                objs_per_slab,
                pages_per_slab,
            )
        )

    # XXX - could be displayed only if we use -v
    print("")
    print("Legend:")
    print("name: slab cache name used for display")
    print("objs: total number of chunks in that slab cache")
    print("inuse: number of allocated chunks in that slab cache")
    print("slabs: number of slabs allocated for that slab cache")
    print("size: chunk size (with metadata)")
    print("obj_size: object size (without metadata)")
    print("objs_per_slab: number of objects per slab")
    print("pages_per_slab: number of pages per slab")
