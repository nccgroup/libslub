import logging
import os
import sys

# Add the root path
module_path = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
if module_path not in sys.path:
    # print("DEBUG: adding module path...")
    sys.path.insert(0, module_path)
# print(sys.path) # DEBUG

import configparser

# Recursively reload modules. Impl based on https://stackoverflow.com/a/66661311/1508881"""
for module in list(sys.modules.keys()):
    if "libslub" in module:
        del sys.modules[module]

import libslub.debugger as d
import libslub.frontend.frontend_gdb as fg
import libslub.logger as logger
import libslub.pydbg.pygdbpython as pgp
import libslub.slub.sb as sb


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
        except (configparser.NoOptionError, configparser.NoSectionError):
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
