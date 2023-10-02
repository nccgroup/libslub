from __future__ import print_function

import logging

import libslub.commands.meta as cmd_meta
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbmeta.py")


class sbmeta(sbcmd.sbcmd):
    """Command to manage metadata for a given address"""

    def __init__(self, sb):
        log.debug("sbmeta.__init__()")
        super(sbmeta, self).__init__(sb, "sbmeta")

        self.parser = cmd_meta.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbmeta.invoke()")
        cmd_meta.slub_meta(self.sb, self.args)
