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
log.trace("sbtrace.py")

class sbtrace(sbcmd.sbcmd):
    """Command to start/stop tracing object allocations for a slab cache"""

    def __init__(self, sb):
        log.debug("sbtrace.__init__()")
        super(sbtrace, self).__init__(sb, "sbtrace")

        self.parser = argparse.ArgumentParser(
            description="""Start/stop tracing object allocations for a slab cache

Setup break points for the specified slab names""", 
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
            "names", nargs="*", default=[],
            help="Slab names (e.g. 'kmalloc-1k')"
        )

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbtrace.invoke()")
        
        if len(self.args.names) == 0:
            print("No slab cache names specified")
            return

        for name in self.args.names:
            slab_cache = sb.sb.find_slab_cache(name)
            if slab_cache is None:
                print("Slab cache '%s' not found" % name)
                return

            if name in self.sb.trace_caches:
                print("Stopped tracing slab cache '%s'" % name)
                self.sb.trace_caches.remove(name)
            else:
                print("Started tracing slab cache '%s'" % name)
                self.sb.trace_caches.append(name)
            self.sb.breakpoints.update_breakpoints()