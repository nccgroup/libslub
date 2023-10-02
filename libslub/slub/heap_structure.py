import logging

log = logging.getLogger("libslub")
log.trace("heap_structure.py")


class heap_structure(object):
    """Represent a general structure. Can be inherited by any structure like malloc_chunk.
    Allow factoring of functions used by many structures, so we don't duplicate code.
    """

    def __init__(self, sb):
        log.trace("heap_structure.__init__()")
        self.sb = sb
        self.initOK = True
        self.dbg = self.sb.dbg

    def validate_address(self, address):
        """Valid that a given address can actually be used as chunk address"""
        log.trace("heap_structure.validate_address()")

        if address is None or address == 0 or not isinstance(address, int):
            print("Invalid address")
            # raise Exception("Invalid address")
            self.initOK = False
            self.address = None
            return False
        else:
            self.address = address
        return True
