# Note: We can't importlib.reload() this file atm because
# otherwise we get an "super(type, obj): obj must be an instance
# or subtype of type" when instanciating
# several classes inheriting from the same ptcmd class.
# See https://thomas-cokelaer.info/blog/2011/09/382/
# This file should not change much anyway but if we modify it, we need to restart gdb
# entirely instead of reloading libslub only

import logging
import shlex
from functools import wraps

import gdb

import libslub.frontend.printutils as pu

log = logging.getLogger("libslub")
log.trace("sbcmd.py")


class sbcmd(gdb.Command):
    """This is a super class with convenience methods shared by all the commands to:
    - parse the command's arguments/options
    - set/reset a logging level (debugging only)
    """

    def __init__(self, sb, name):
        self.sb = sb

        if self.sb.dbg is None:
            pu.print_error("Please specify a debugger")
            raise Exception("sys.exit()")

        self.name = name
        self.old_level = None
        self.parser = None  # ArgumentParser
        self.description = None  # Only use if not in the parser

        super(sbcmd, self).__init__(name, gdb.COMMAND_DATA, gdb.COMPLETE_NONE)

    @property
    def version(self):
        """Easily access the version string without going through the slab object"""
        return self.sb.version

    @property
    def dbg(self):
        """Easily access the pydbg object without going through the slab object"""
        return self.sb.dbg

    @property
    def cache(self):
        """Easily access the cache object without going through the slab object"""
        return self.sb.cache

    def set_loglevel(self, loglevel):
        """Change the logging level. This is changed temporarily for the duration
        of the command since reset_loglevel() is called at the end after the command is executed
        """
        if loglevel is not None:
            numeric_level = getattr(logging, loglevel.upper(), None)
            if not isinstance(numeric_level, int):
                print("WARNING: Invalid log level: %s" % loglevel)
                return
            self.old_level = log.getEffectiveLevel()
            # print("old loglevel: %d" % self.old_level)
            # print("new loglevel: %d" % numeric_level)
            log.setLevel(numeric_level)

    def reset_loglevel(self):
        """Reset the logging level to the previous one"""
        if self.old_level is not None:
            # print("restore loglevel: %d" % self.old_level)
            log.setLevel(self.old_level)
            self.old_level = None

    def init_and_cleanup(f):
        """Decorator for a command's invoke() method

        This allows:
        - not having to duplicate the argument parsing in all commands
        - not having to reset the log level before each of the "return"
          in the invoke() of each command
        """

        @wraps(f)
        def _init_and_cleanup(self, arg, from_tty):
            try:
                self.args = self.parser.parse_args(shlex.split(arg))
            except SystemExit:
                # If we specified an unsupported argument/option, argparse will try to call sys.exit()
                # which will trigger such an exception, so we can safely catch it to avoid error messages
                # in gdb
                # h.show_last_exception()
                # raise e
                return
            if self.args.help:
                self.parser.print_help()
                # h.print_subparser_help(self.parser)

                return
            self.set_loglevel(self.args.loglevel)
            f(self, arg, from_tty)  # Call actual invoke()
            self.reset_loglevel()

        return _init_and_cleanup
