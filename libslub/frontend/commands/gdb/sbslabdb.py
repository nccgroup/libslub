from __future__ import print_function

import logging

import libslub.commands.db as cmd_db
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbslabdb.py")


class sbslabdb(sbcmd.sbcmd):
    """Command to add/delete known slab addresses when they are created/deleted

    This is an alternative way to save slab addresses to "sbwatch" since gdb breakpoints in Python
    crash gdb a lot..."""

    def __init__(self, sb):
        log.debug("sbslabdb.__init__()")
        super(sbslabdb, self).__init__(sb, "sbslabdb")

        self.parser = cmd_db.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbslabdb.invoke()")
        cmd_db.slub_db(self.sb, self.args)
