from __future__ import print_function

import logging

import libslub.commands.watch as cmd_watch
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbwatch.py")


class sbwatch(sbcmd.sbcmd):
    """Command to start/stop watching full-slabs for a slab cache"""

    def __init__(self, sb):
        log.debug("sbwatch.__init__()")
        super(sbwatch, self).__init__(sb, "sbwatch")
        self.parser = cmd_watch.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbwatch.invoke()")
        cmd_watch.slub_watch(self.sb, self.args)
