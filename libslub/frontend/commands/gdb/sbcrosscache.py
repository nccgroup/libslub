from __future__ import print_function

import argparse
import struct
import sys
import logging
import importlib
import gdb

import libslub.frontend.printutils as pu
importlib.reload(pu)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.frontend.helpers as h
importlib.reload(h)
import libslub.frontend.commands.gdb.sbcmd as sbcmd
#importlib.reload(sbcmd)

log = logging.getLogger("libslub")
log.trace("sbcrosscache.py")

class sbcrosscache(sbcmd.sbcmd):
    """Command to identify adjacent memory regions from two different slabs"""

    def __init__(self, sb):
        log.debug("sbcrosscache.__init__()")
        super(sbcrosscache, self).__init__(sb, "sbcrosscache")

        self.parser = argparse.ArgumentParser(
            description="""Identify adjacent memory regions from two different slabs

This is particularly useful when you want to do cross cache attacks.""", 
            add_help=False,
            formatter_class=argparse.RawTextHelpFormatter,
        )
        self.parser.add_argument(
            "-h", "--help", dest="help", action="store_true", default=False,
            help="Show this help"
        )
        # allows to enable a different log level during development/debugging
        self.parser.add_argument(
            "--loglevel", dest="loglevel", default=None,
            help=argparse.SUPPRESS
        )

        self.parser.add_argument(
            "slab_cache_a", default=None,
            help="First slab cache name (e.g. 'kmalloc-64')"
        )

        self.parser.add_argument(
            "slab_cache_b", default=None,
            help="Second slab cache name (e.g. 'kmalloc-96')"
        )

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbcrosscache.invoke()")

        slab_cache_a = self.args.slab_cache_a
        slab_cache_b = self.args.slab_cache_b

        a = sb.sb.find_slab_cache(slab_cache_a)
        if a is None:
            print("Slab cache '%s' not found" % slab_cache_a)
            return

        b = sb.sb.find_slab_cache(slab_cache_b)
        if a is None:
            print("Slab cache '%s' not found" % slab_cache_b)
            return

        a_pages = self.sb.get_slab_cache_memory_pages(a)
        b_pages = self.sb.get_slab_cache_memory_pages(b)

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