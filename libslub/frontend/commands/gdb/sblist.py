from __future__ import print_function

import logging

import libslub.commands.list as cmd_list
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sblist.py")


class sblist(sbcmd.sbcmd):
    """Command to show information about all the slab caches on the system"""

    def __init__(self, sb):
        log.debug("sblist.__init__()")
        super(sblist, self).__init__(sb, "sblist")

        self.parser = cmd_list.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        cmd_list.slub_list(self.sb, self.args)
