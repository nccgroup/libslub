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
import libslub.slub.kmem_cache as kc
importlib.reload(kc)
import libslub.frontend.commands.gdb.sbobject as sbobject
importlib.reload(sbobject)
import libslub.frontend.commands.gdb.sbcmd as sbcmd
#importlib.reload(sbcmd)

log = logging.getLogger("libslub")
log.trace("sbcache.py")

class sbcache(sbcmd.sbcmd):
    """Command to print the metadata and contents of one or all slab cache(s)"""

    def __init__(self, sb):
        log.debug("sbcache.__init__()")
        super(sbcache, self).__init__(sb, "sbcache")

        self.parser = argparse.ArgumentParser(
            description="""Print the metadata and contents of one or all slab cache(s)

If you don't specify any slab cache name, it will print all of them but it will take some time to parse structures in memory""", 
            add_help=False,
            formatter_class=argparse.RawTextHelpFormatter,
        )
        # "sbobject" also has this argument but default for 
        # "sbcache" is to show unlimited number of chunks
        self.parser.add_argument(
            "-c", "--count", dest="count", type=h.check_count_value_positive, default=None,
            help="""Number of chunks to print linearly in each slab or in each freelist"""
        )
        # XXX - is it a feature we want for filtering too?
        #self.parser.add_argument(
        #    "-C", "--count-slab", dest="count_slab", type=h.check_count_value_positive, default=None,
        #    help="""Number of slabs to print for each cpu"""
        #)
        self.parser.add_argument(
            "--cpu", dest="cpu", type=int, default=None,
            help="""Show CPU specified only, instead of all slabs (Ignore node's partial slabs and full slabs)"""
        )
        self.parser.add_argument(
            "--main-slab", dest="main_slab", action="store_true", default=None,
            help="""Show main slabs for CPUs only, instead of all slabs (Ignore CPU partial slabs, node's partial slabs and full slabs)"""
        )
        self.parser.add_argument(
            "--partial-slab", dest="partial_slab", action="store_true", default=None,
            help="""Show partial slabs for CPUs only, instead of all slabs (Ignore CPU main slabs, node's partial slabs and full slabs)"""
        )
        self.parser.add_argument(
            "--node-slab", dest="node_slab", action="store_true", default=None,
            help="""Show partial slabs for nodes only, instead of all slabs (Ignore CPU main/partial slabs and node's full slabs)"""
        )
        self.parser.add_argument(
            "--full-slab", dest="full_slab", action="store_true", default=None,
            help="""Show full slabs only, instead of all slabs (Ignore CPU main and partial slabs, node's partial slabs)"""
        )
        self.parser.add_argument(
            "--show-freelist", dest="show_freelist", action="store_true", default=None,
            help="""Show the freelists for each slab (not shown by default)"""
        )
        self.parser.add_argument(
            "--show-lockless-freelist", dest="show_lockless_freelist", action="store_true", default=None,
            help="""Show the freelist associated to a CPU for the main slab (not shown by default)"""
        )
        self.parser.add_argument(
            "--show-region", dest="show_region", action="store_true", default=None,
            help="""Show the objects in the memory region for each slab (not shown by default)"""
        )
        self.parser.add_argument(
            "--hide-title", dest="hide_title", action="store_true", default=False,
            help="""Hide the "region:" or "freelist:" titles (shown by default) when showing regions or freelists"""
        )
        self.parser.add_argument(
            "--object-only", dest="object_only", action="store_true", default=None,
            help="""Do not show structures' fields and show objects only (still requires --show-freelist and/or --show-region)"""
        )
        # other arguments are implemented in the "sbobject" command
        # and will be shown after the above
        sbobject.sbobject.add_arguments(self)

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbcache.invoke()")

        self.sb.cache.update_all(name=self.args.name, show_status=self.args.debug, use_cache=self.args.use_cache)
        self.args.use_cache = True # we can use the cache from now on

        log.debug("sbcache.invoke() (2)")

        # Prepare fake arguments for "sbobject" format
        self.args.addresses = ["0x0"] # won't use it until we parse actual memory regions
                                      # where we will parse cached memory regions directly at that time anyway
        ret = sbobject.sbobject.parse_arguments(self)
        if ret == None:
            return
        addresses, self.highlight_addresses, self.highlight_metadata, self.highlight_types = ret

        # this is not a real user argument but is used internally to know if we need to print stuff
        self.output_filtered = False
        self.cpu_filtered = False
        if self.args.main_slab is True or self.args.partial_slab is True \
            or self.args.node_slab is True or self.args.full_slab is True:
            self.output_filtered = True
        if self.args.cpu is not None:
            self.cpu_filtered = True
        if self.args.cpu is not None and (self.args.node_slab is True or self.args.full_slab is True) \
            and self.args.main_slab is not True and self.args.partial_slab is not True:
            print("WARNING: --cpu will be ignored")

        name = self.args.name
        if name != None and name in self.sb.cache.slab_caches.keys():
            self.sb.cache.slab_caches[name].print(cmd=self)
        elif name == None:
            for name, kmem_cache in self.sb.cache.slab_caches.items():
                kmem_cache.print(cmd=self)
        return