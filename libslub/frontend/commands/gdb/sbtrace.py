from __future__ import print_function

import logging

import libslub.commands.trace as cmd_trace
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbtrace.py")


class sbtrace(sbcmd.sbcmd):
    """Command to start/stop tracing object allocations for a slab cache"""

    def __init__(self, sb):
        log.debug("sbtrace.__init__()")
        super(sbtrace, self).__init__(sb, "sbtrace")
        self.parser = cmd_trace.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbtrace.invoke()")
        cmd_trace.slub_trace(self.sb, self.args)
