from abc import ABC, abstractmethod

import libslub.frontend.helpers as helpers
import libslub.frontend.printutils as pu


# Globals functions are used by the debugger interface
# TODO: The should just be made defaults of the interface probably, but I'm not sure if that works with abstractmethod
def search_chunk(dbg, address, size, search_value, search_type, depth=0):
    """Searches a chunk for a specific value of a given type
    Includes the chunk header in the search by default

    :param dbg: debugger object
    :param address: slub chunk address
    :param size: slub chunk size
    :param search_value: string representing what to search for
    :param search_type: "byte", "word", "dword", "qword" or "string"
    :param depth: How far into each chunk to search, starting from chunk header address
    :param skip: True if don't include chunk header contents in search results
    :return: True if the value was found, False otherwise

    Note: this method is generic and does not need a debugger-specific implementation
    """
    if depth == 0 or depth > size:
        depth = size

    try:
        result = dbg.search(
            address, address + depth, search_value, search_type=search_type
        )
        return result
    except Exception as e:
        print(f"WARNING: slab chunk search failed: {e}")
        return False


class DebuggerInterface(ABC):
    """Python abstraction interface that allows calling into any specific debugger APIs

    Any debugger implementation should implement the methods called on self.debugger
    """

    @abstractmethod
    def execute(self, to_string=True):
        """Execute a command in the debugger CLI"""
        pass

    @abstractmethod
    def is_32bit(self):
        """Check if the target is 32-bit or not"""
        pass

    @abstractmethod
    def is_64bit(self):
        """Check if the target is 64-bit or not"""
        pass

    @abstractmethod
    def is_alive(self):
        """Check if the target is alive or not"""
        pass

    @abstractmethod
    def get_arch_name(self):
        """Get target architecture name"""
        pass

    @abstractmethod
    def get_kernel_version(self):
        """Get the kernel version"""
        pass

    @abstractmethod
    def read_memory(self, address, length):
        """Read bytes at the given address of the given length"""
        pass

    @abstractmethod
    def parse_variable(self, variable):
        """Parse and evaluate a debugger variable expression"""
        pass

    @abstractmethod
    def parse_address(self, addresses):
        """Parse one or more addresses or debugger variables

        :param address: an address string containing hex, int, or debugger variable
        :return: the resolved addresses as integers

        It this should be able to handle: hex, decimal, program variables
        with or without special characters (like $, &, etc.),
        basic addition and subtraction of variables, etc.
        """
        pass

    @abstractmethod
    def print_hexdump(self, address, size, unit=8):
        """Hexdump data to stdout

        :param address: starting address
        :param size: number of bytes from the address
        :param unit: hexdump unit (e.g. 1, 2, 4, 8, "dps")
        """

        pass

    @abstractmethod
    def search(self, start_address, end_address, search_value, search_type="string"):
        """Find a value within some address range

        :param start_address: where to start searching
        :param end_address: where to end searching
        :param search_value: string representing what to search for
        :param search_type: "byte", "word", "dword", "qword" or "string"
        :return: True if the value was found, False otherwise
        """
        pass

    @abstractmethod
    def warning(self, msg):
        """Print a warning message"""
        pass

    @abstractmethod
    def error(self, msg):
        """Print an error message"""
        pass

    @abstractmethod
    def get_backtrace(self):
        """Get the current backtrace"""
        pass

    @abstractmethod
    def get_page_address(self, page):
        """Get the virtual address for the given page address"""
        pass


class pydbg(DebuggerInterface):
    """Python abstraction interface that allows calling into any specific debugger APIs

    Any debugger implementation should implement the methods called on self.debugger
    """

    def __init__(self, debugger):
        """Initialize the debugger to be used for any future API"""
        self.debugger = debugger

    def execute(self, cmd, to_string=True):
        """Execute a command in the debugger CLI"""
        return self.debugger.execute(cmd, to_string=to_string)

    def is_32bit(self):
        """Check if the target is 32-bit or not"""
        return self.debugger.get_ptrsize() == 4

    def is_64bit(self):
        """Check if the target is 64-bit or not"""
        return self.debugger.get_ptrsize() == 8

    def get_arch_name(self):
        """Get target architecture name"""
        return self.debugger.get_arch_name()

    def get_kernel_version(self):
        """Get the kernel version"""
        # HACK: We only support one kernel version for now, this should
        # correspond to whatever you are using in the breakpoint_table in breakpoints.py
        return "Ubuntu 5.15.0-27.28-generic"
        # return self.debugger.get_kernel_version()

    def is_alive(self):
        """Check if the target is alive or not"""
        return self.debugger.is_alive()

    def read_memory(self, address, length):
        """Read bytes at the given address of the given length"""
        return self.debugger.read_memory(address, length)

    def parse_variable(self, variable):
        """Parse and evaluate a debugger variable expression"""
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

    def print_hexdump(self, address, size, unit=8):
        """Hexdump data to stdout

        :param address: starting address
        :param size: number of bytes from the address
        :param unit: hexdump unit (e.g. 1, 2, 4, 8, "dps")
        """

        self.debugger.print_hexdump(address, size, unit=unit)

    def search(self, start_address, end_address, search_value, search_type="string"):
        return self.debugger.search(
            start_address, end_address, search_value, search_type=search_type
        )

    def warning(self, msg):
        """Print a warning message"""
        pu.print_error(msg)

    def error(self, msg):
        """Print an error message"""
        pu.print_error(msg)

    def show_exception(self):
        """Print the last exception"""
        helpers.show_last_exception()

    def get_backtrace(self):
        return helpers.get_backtrace()

    def get_page_address(self, page):
        """Comes from arch/x86/include/asm/page_64_types.h
        #define __PAGE_OFFSET_BASE_L4 _AC(0xffff888000000000, UL)
        """
        # NOTE: This won't work on 5-level paging
        # Some configurations it stored in this variable, but it isnt queriable
        # foo = gdb.lookup_global_symbol("__ro_after_init").value()
        if "x86-64" in self.get_arch_name():
            offset = (page - 0xFFFFEA0000000000) >> 6 << 0xC
            return (
                # 0xFFFF880000000000 + offset
                0xFFFF888000000000
                + offset
            )  # this value depends on kernel version if could be 0xFFFF888000000000
        else:
            # TODO: Does this actually work on aarch64?
            UNSIGNED_LONG = 0xFFFFFFFFFFFFFFFF
            memstart_addr = int(self.memstart_addr) & UNSIGNED_LONG
            addr = (memstart_addr >> 6) & UNSIGNED_LONG
            addr = (addr & 0xFFFFFFFFFF000000) & UNSIGNED_LONG
            addr = (0xFFFFFFBDC0000000 - addr) & UNSIGNED_LONG
            addr = (page - addr) & UNSIGNED_LONG
            addr = (addr >> 6 << 0xC) & UNSIGNED_LONG
            addr = (addr - memstart_addr) & UNSIGNED_LONG
            return addr | 0xFFFFFFC000000000
