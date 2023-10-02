from __future__ import print_function

import logging

import libslub.commands.crosscache as cmd_crosscache
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h
import libslub.slub.sb as sb

log = logging.getLogger("libslub")
log.trace("sbcrosscache.py")


class sbcrosscache(sbcmd.sbcmd):
    """Command to identify adjacent memory regions from two different slabs"""

    def __init__(self, sb):
        log.debug("sbcrosscache.__init__()")
        super(sbcrosscache, self).__init__(sb, "sbcrosscache")
        self.parser = cmd_crosscache.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbcrosscache.invoke()")
        cmd_crosscache.slub_crosscache(sb, self.args)
