from __future__ import print_function

import logging

import libslub.commands.breaks as cmd_break
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbbreak.py")


class sbbreak(sbcmd.sbcmd):
    """Command to start/stop breaking on object allocations for a slab cache"""

    def __init__(self, sb):
        log.debug("sbbreak.__init__()")
        super(sbbreak, self).__init__(sb, "sbbreak")
        self.parser = cmd_break.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbbreak.invoke()")
        cmd_break.slub_break(self.sb, self.args)
