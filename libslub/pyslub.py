import configparser
import logging
import os
import sys

import libslub.debugger as d
import libslub.frontend.frontend_gdb as fg
import libslub.logger as logger
import libslub.pydbg.pygdbpython as pgp
import libslub.slub.sb as sb

# This file is used if you're not loading the module from a different framework like pwndbg


class pyslab:
    """Entry point of libslub"""

    def __init__(self):
        # Setup GDB debugger interface
        debugger = pgp.pygdbpython()
        self.dbg = d.pydbg(debugger)

        config = configparser.SafeConfigParser()
        path = os.path.abspath(os.path.dirname(__file__))
        config_path = os.path.join(path, "libslub.cfg")
        config.read(config_path)

        try:
            breakpoints_enabled = config.getboolean("Slab", "breakpoints_enabled")
        except configparser.NoOptionError:
            breakpoints_enabled = False

        self.sb = sb.Slub(debugger=self.dbg, breakpoints_enabled=breakpoints_enabled)

        # Register GDB commands
        fg.frontend_gdb(self.sb)


try:
    log
except Exception:
    log = logging.getLogger("libslub")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logger.MyFormatter(datefmt="%H:%M:%S"))
    log.addHandler(handler)

# This allows changing the log level and reloading in gdb even if the logger was already defined
# XXX - however this file is not reloaded early when we reload in gdb, so we need to re-source in gdb 2x
# for the logger level to be changed atm
# log.setLevel(logging.TRACE) # use for debugging reloading .py files only
# log.setLevel(logging.DEBUG) # all other types of debugging
log.setLevel(logging.NOTSET)

if log.isEnabledFor(logging.TRACE):
    log.warning("logging TRACE enabled")
elif log.isEnabledFor(logging.DEBUG):
    log.warning("logging DEBUG enabled")
# elif log.isEnabledFor(logging.INFO):
#     log.warning(f"logging INFO enabled")
# elif log.isEnabledFor(logging.WARNING):
#     log.warning(f"logging WARNING enabled")

log.trace("libslub/pyslub.py")
pyslab()
