from __future__ import print_function

import logging

import libslub.commands.object as cmd_object
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbobject.py")


class sbobject(sbcmd.sbcmd):
    """Command to print information about objects aka chunk(s) inside a memory region
    associated with a slab
    """

    def __init__(self, sb):
        log.debug("sbobject.__init__()")
        super(sbobject, self).__init__(sb, "sbobject")
        self.parser = cmd_object.generate_parser(self.name)

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbobject.invoke()")
        cmd_object.slub_object(self.sb, self.args)
        return
