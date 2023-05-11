import importlib

import libslub.frontend.helpers as h
importlib.reload(h)

class pydbg:
    """Python abstraction interface that allows calling into any specific debugger APIs

    Any debugger implementation should implement the methods called on self.debugger
    """
    
    def __init__(self, debugger):
        """Initialize the debugger to be used for any future API
        """
        self.debugger = debugger

    def execute(self, cmd, to_string=True):
        """Execute a command in the debugger CLI
        """
        return self.debugger.execute(cmd, to_string=to_string)


    def get_size_sz(self):
        """Retrieve the size_t size for the current architecture
        """
        return self.debugger.get_size_sz()

    def read_memory(self, address, length):
        """Read bytes at the given address of the given length
        """
        return self.debugger.read_memory(address, length)

    def parse_variable(self, variable):
        """Parse and evaluate a debugger variable expression
        """
        return self.debugger.parse_variable(variable)

    def parse_address(self, addresses):
        """Parse one or more addresses or debugger variables

        :param address: an address string containing hex, int, or debugger variable
        :return: the resolved addresses as integers

        It this should be able to handle: hex, decimal, program variables
        with or without special characters (like $, &, etc.),
        basic addition and subtraction of variables, etc.
        """
        return self.debugger.parse_address(addresses)

    def print_hexdump_chunk(self, sb, o, maxlen=0, off=0, debug=False, unit=8, verbose=1):
        """Hexdump chunk data to stdout
        
        :param sb: slab object
        :param o: obj() object representing the chunk
        :param maxlen: maximum amount of bytes to hexdump
        :param off: offset into the chunk's data to hexdump (after the malloc_chunk header)
        :param debug: debug enabled or not
        :param unit: hexdump unit (e.g. 1, 2, 4, 8, "dps")
        :param verbose: see ptchunk's ArgumentParser definition
        """

        address = o.address + off
        size = o.size - off
        if size <= 0:
            print("[!] Chunk corrupt? Bad size")
            return
        print("0x%x bytes of object data:" % size)
        shown_size = size
        if maxlen != 0:
            if shown_size > maxlen:
                shown_size = maxlen

        self.print_hexdump(address, shown_size, unit=unit)

    def print_hexdump(self, address, size, unit=8):
        """Hexdump data to stdout

        :param address: starting address
        :param size: number of bytes from the address
        :param unit: hexdump unit (e.g. 1, 2, 4, 8, "dps")
        """

        self.debugger.print_hexdump(address, size, unit=unit)
