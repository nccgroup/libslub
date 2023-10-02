from __future__ import print_function

import logging

import libslub.commands.help as cmd_help
import libslub.frontend.commands.gdb.sbcmd as sbcmd
import libslub.frontend.helpers as h

log = logging.getLogger("libslub")
log.trace("sbhelp.py")


class sbhelp(sbcmd.sbcmd):
    """Command to list all available commands"""

    def __init__(self, sb):
        log.debug("sbhelp.__init__()")
        super(sbhelp, self).__init__(sb, "sbhelp")
        self.parser = cmd_help.generate_parser()

    @h.catch_exceptions
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html

        Print the usage of all the commands
        """
        cmd_help.slub_help(self.sb)
        print(
            "Note: Modify libslub.cfg if you want to enable or disable sbbreak/sbtrace/sbwatch commands (may crash GDB due to broken finish)"
        )
