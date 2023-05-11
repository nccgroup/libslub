import sys
import logging
import re
import importlib
import hexdump
from pathlib import Path
from functools import wraps
import gdb

import libslub.frontend.printutils as pu
importlib.reload(pu)

log = logging.getLogger("libslub")
log.trace("pygdbpython.py")

# XXX - could have that into a helper.py instead?
def gdb_is_running(f):
    """Decorator to make sure gdb is running
    """

    @wraps(f)
    def _gdb_is_running(*args, **kwargs):
        if gdb.selected_thread() is not None:
            return f(*args, **kwargs)
        else:
            pu.print_error("GDB is not running.")

    return _gdb_is_running

class pygdbpython:
    """Debugger bridge calling into gdb-specific APIs
    
    See debugger.py interface
    """

    def __init__(self):
        log.debug("pygdbpython.__init__()")

        self.inferior = None
        self.SIZE_SZ = 0

    #
    # Methods from the debugger abstraction
    #

    @gdb_is_running
    def execute(self, cmd, to_string=True):
        """See debugger.py interface
        """

        log.debug("pygdbpython.execute()")
        return gdb.execute(cmd, to_string=to_string)

    @gdb_is_running
    def get_size_sz(self):
        """See debugger.py interface
        """
        return 8 # hardcoded for now

    @gdb_is_running
    def read_memory(self, address, length):
        """See debugger.py interface
        """
        
        if log.level <= logging.DEBUG:
            if type(address) == int:
                printed_address = "0x%x" % address
            else:
                printed_address = str(address)
            if type(length) == int:
                printed_length = "0x%x" % length
            else:
                printed_length = str(length)
            log.debug(f"pygdbpython.read_memory({printed_address}, {printed_length})")
        if self.inferior is None:
            self.inferior = self.get_inferior()

        return self.inferior.read_memory(address, length)

    @gdb_is_running
    def parse_variable(self, variable=None):
        """See debugger.py interface
        """
        log.debug("pygdbpython.parse_variable()")

        if variable is None:
            pu.print_error("Please specify a variable to read")
            return None

        evaluated = int(gdb.parse_and_eval(variable))
        log.info("pygdbpython.parse_variable(): evaluated variable = 0x%x" % evaluated)
        if self.get_size_sz() == 4:
            p = self.tohex(evaluated, 32)
        elif self.get_size_sz() == 8:
            p = self.tohex(evaluated, 64)
        return int(p, 16)

    @gdb_is_running
    def print_hexdump(self, address, size, unit=8):
        """See debugger.py interface
        """

        # See https://visualgdb.com/gdbreference/commands/x
        if unit == 1:
            #cmd = "x/%dbx 0x%x\n" % (size, address)
            try:
                mem = self.read_memory(address, size)
            except TypeError:
                pu.print_error("Invalid address specified")
                return
            except RuntimeError:
                pu.print_error("Could not read address {0:#x}".format(addr))
                return
            i = 0
            for line in hexdump.hexdump(bytes(mem), result='generator'):
                elts = line.split(":")
                txt = ":".join(elts[1:])
                print("0x%x: %s" % (address+i*0x10, txt))
                i += 1
            return
        elif unit == 2:
            cmd = "x/%dhx 0x%x\n" % (size/2, address)
        elif unit == 4:
            cmd = "x/%dwx 0x%x\n" % (size/4, address)
        elif unit == 8:
            cmd = "x/%dgx 0x%x\n" % (size/8, address)
        elif unit == "dps":
            # XXX - call into dps_like_for_gdb.py command for now
            # but we want to just add it to libslub maybe
            cmd = "dps 0x%x %d\n" % (address, size/self.get_size_sz())
        else:
            print("[!] Invalid unit specified")
            return
        print(self.execute(cmd, to_string=True))
        return

    def parse_address(self, addresses):
        """See debugger.py interface

        It should be able to handle gdb variables starting with $ or if we ommit it too
        """

        log.debug("pygdbpython.parse_address()")
        resolved = []
        if type(addresses) != list:
            addresses = [addresses]
        for item in addresses:
            addr = None
            try:
                # This should parse most cases like integers,
                # variables (exact name), registers (if we specify $ in front), as well
                # as arithmetic with integers, variables and registers.
                # i.e. as long as "p ABC" or "x /x ABC" works, it should work within here too
                addr = self.parse_variable(item)
                log.info("parsed address (default) = 0x%x" % addr)
            except:
                # XXX - Not sure what this is for?
                try:
                    addr = self.parse_variable("&" + item)
                    log.info("parsed address (unknown) = 0x%x" % addr)
                except:
                    # Parse registers if we don't specify the register, e.g. "rdi" instead of "$rdi"
                    try:
                        addr = self.parse_variable("$" + item)
                        log.info("parsed address (register) = 0x%x" % addr)
                    except:
                        pu.print_error(f"ERROR: Unable to parse {item}")
                        continue
            if addr is not None:
                resolved.append(addr)
        return resolved

    #
    # gdb-specific methods
    #

    def get_inferior(self):
        """Get the gdb inferior, used for other gdb commands
        """

        log.debug("pygdbpython.get_inferior()")
        try:
            if self.inferior is None:
                if len(gdb.inferiors()) == 0:
                    pu.print_error("No gdb inferior could be found.")
                    return -1
                else:
                    self.inferior = gdb.inferiors()[0]
                    return self.inferior
            else:
                return self.inferior
        except AttributeError:
            pu.print_error("This gdb's python support is too old.")
            raise Exception("sys.exit()")

    # XXX - move to generic helper shared by all debuggers?
    def tohex(self, val, nbits):
        """Handle gdb adding extra char to hexadecimal values
        """

        log.debug("pygdbpython.tohex()")
        result = hex((val + (1 << nbits)) % (1 << nbits))
        # -1 because hex() only sometimes tacks on a L to hex values...
        if result[-1] == "L":
            return result[:-1]
        else:
            return result