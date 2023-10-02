import argparse


def generate_parser():
    parser = argparse.ArgumentParser(
        description="""Identify adjacent memory regions from two different slabs

This is particularly useful when you want to do cross cache attacks.""",
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
        "slab_cache_a",
        default=None,
        help="First slab cache name (e.g. 'kmalloc-64')",
    )

    parser.add_argument(
        "slab_cache_b",
        default=None,
        help="Second slab cache name (e.g. 'kmalloc-96')",
    )
    return parser


def slub_crosscache(
    sb,
    args,
):
    slab_cache_a = args.slab_cache_a
    slab_cache_b = args.slab_cache_b

    a = sb.Slub.find_slab_cache(slab_cache_a)
    if a is None:
        print("Slab cache '%s' not found" % slab_cache_a)
        return

    b = sb.Slub.find_slab_cache(slab_cache_b)
    if a is None:
        print("Slab cache '%s' not found" % slab_cache_b)
        return

    a_pages = sb.get_slab_cache_memory_pages(a)
    b_pages = sb.get_slab_cache_memory_pages(b)

    a_pages.sort()
    b_pages.sort()

    for a_page in a_pages:
        if a_page < b_pages[0] - 4096 or a_page > b_pages[-1] + 4096:
            continue
        first = True
        for b_page in b_pages:
            if a_page == b_page - 4096:
                if first:
                    print("---")
                    first = False
                    print(f"0x{a_page:08x} - {slab_cache_a}")
                print(f"0x{b_page:08x} - {slab_cache_b}")
            elif a_page == b_page + 4096:
                if first:
                    print("---")
                    first = False
                print(f"0x{b_page:08x} - {slab_cache_b}")
                print(f"0x{a_page:08x} - {slab_cache_a}")
        pass
