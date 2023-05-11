from __future__ import print_function

import sys
import logging
import importlib
import gdb

import libslub.frontend.printutils as pu
importlib.reload(pu)
import libslub.slub.sb as sb
importlib.reload(sb)
import libslub.frontend.helpers as h
importlib.reload(h)
import libslub.frontend.commands.gdb.sbcmd as sbcmd
#importlib.reload(sbcmd)

log = logging.getLogger("libslub")
log.trace("sbhelp.py")

class sbhelp(sbcmd.sbcmd):
    """Command to list all available commands"""

    def __init__(self, sb, commands=[]):
        log.debug("sbhelp.__init__()")
        super(sbhelp, self).__init__(sb, "sbhelp")

        self.cmds = commands

    @h.catch_exceptions
    def invoke(self, arg, from_tty):
        """Inherited from gdb.Command
        See https://sourceware.org/gdb/current/onlinedocs/gdb/Commands-In-Python.html

        Print the usage of all the commands
        """

        pu.print_header("{:<20}".format("sbhelp"), end="")
        print("List all libslub commands")
        for cmd in self.cmds:
            if cmd.parser != None:
                # Only keep the first line of the description which should be short
                description = cmd.parser.description.split("\n")[0]
            elif cmd.description != None:
                description = cmd.description
            else:
                description = "Unknown"
            pu.print_header("{:<20}".format(cmd.name), end="")
            print(description)
        print("Note: Use a command name with -h to get additional help")
        print("Note: Modify libslub.cfg if you want to enable or disable sbbreak/sbtrace/sbwatch commands (may crash GDB due to broken finish)")