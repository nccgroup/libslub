from __future__ import print_function

import logging

import libslub.commands.cache as cmd_cache
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbcache.py")


class sbcache(sbcmd.sbcmd):
    """Command to print the metadata and contents of one or all slab cache(s)"""

    def __init__(self, sb):
        log.debug("sbcache.__init__()")
        super(sbcache, self).__init__(sb, "sbcache")

        self.parser = cmd_cache.generate_parser()

    @h.catch_exceptions
    @sbcmd.sbcmd.init_and_cleanup
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html
        """

        log.debug("sbcache.invoke()")
        cmd_cache.slub_cache(self.sb, self.args)
        return
