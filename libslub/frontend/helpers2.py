import argparse
import struct
import sys
import traceback
import gdb
import shlex
import logging
from functools import wraps, lru_cache

log = logging.getLogger("libslub")
log.trace("sb.py")

# START GEF STUFF

# GEF stuff. This is stuff I took from gef for now, that we could probably
# replace with something from lib ptmalloc or whatever

def is_alive():
    """Check if GDB is running."""
    try:
        return gdb.selected_inferior().pid > 0
    except Exception:
        return False
    return False


def cached_lookup_type(_type):
    try:
        return gdb.lookup_type(_type).strip_typedefs()
    except RuntimeError:
        return None


def _ptr_width():
    void = cached_lookup_type("void")
    if void is None:
        uintptr_t = cached_lookup_type("uintptr_t")
        return uintptr_t.sizeof
    else:
        return void.pointer().sizeof


@lru_cache()
def is_64bit():
    """Checks if current target is 64bit."""
    return _ptr_width() == 8


@lru_cache()
def is_32bit():
    """Checks if current target is 32bit."""
    return _ptr_width() == 4


def get_memory_alignment(in_bits=False):
    """Try to determine the size of a pointer on this system.
    First, try to parse it out of the ELF header.
    Next, use the size of `size_t`.
    Finally, try the size of $pc.
    If `in_bits` is set to True, the result is returned in bits, otherwise in
    bytes."""
    if is_32bit():
        return 4 if not in_bits else 32
    elif is_64bit():
        return 8 if not in_bits else 64

    res = cached_lookup_type("size_t")
    if res is not None:
        return res.sizeof if not in_bits else res.sizeof * 8

    try:
        return gdb.parse_and_eval("$pc").type.sizeof
    except:
        pass
    raise EnvironmentError("GEF is running under an unsupported mode")


def style_byte(b, color=True):
    sbyte = "{:02x}".format(b)
    return sbyte


def hexdump(
    source,
    length=0x10,
    separator=".",
    show_raw=False,
    show_symbol=False,
    base=0x00,
    pad=0,
):
    """Return the hexdump of `src` argument.
    @param source *MUST* be of type bytes or bytearray
    @param length is the length of items per line
    @param separator is the default character to use if one byte is not printable
    @param show_raw if True, do not add the line nor the text translation
    @param base is the start address of the block being hexdump
    @return a string with the hexdump"""
    result = []
    align = get_memory_alignment() * 2 + 2 if is_alive() else 18

    for i in range(0, len(source), length):
        chunk = bytearray(source[i : i + length])
        hexa = " ".join([style_byte(b, color=not show_raw) for b in chunk])

        if show_raw:
            result.append(hexa)
            continue

        text = "".join([chr(b) if 0x20 <= b < 0x7F else separator for b in chunk])
        if show_symbol:
            sym = gdb_get_location_from_symbol(base + i)
            sym = "<{:s}+{:04x}>".format(*sym) if sym else ""
        else:
            sym = ""

        result.append(
            "{padding}{addr:#0{aw}x} {sym} {data:<{dw}} {text}".format(
                padding=" " * pad,
                aw=align,
                addr=base + i,
                sym=sym,
                dw=3 * length,
                data=hexa,
                text=text,
            )
        )
    return "\n".join(result)


# END GEF STUFF

def get_breakpoint_list():
    """return a itemized list of breakpoints"""
    break_list = gdb.execute("info breakpoints", to_string=True)
    breakpoints = []
    for line in break_list.split("\n"):
        if not len(line) or line.startswith("Num"):
            continue

        if line.startswith("No breakpoints"):
            break

        items = list(filter(None, line.split(" ")))
        # Skip "breakpoint already hit N times"
        if "breakpoint" in items[0]:
            continue
        num = items[0]
        try:
            int(num)
            # could be useful if later a multiple breakpoint is encountered
            prev_num = num
        except:
            try:
                float(num)
                # multiple breakpoint detected
            except:
                continue
        if len(items) != 7 and len(items) != 9:
            continue
        if len(items) == 7:
            # multiple breakpoint needs to use previously saved bp num
            num = prev_num
            address = items[2]
            function = items[4]
            source = items[6]
        elif len(items) == 9:
            address = items[4]
            function = items[6]
            source = items[8]
        breakpoints.append(
            {"id": num, "address": address, "function": function, "location": source}
        )

    return breakpoints


def find_existing_breakpoints(location, single=False):
    source_bp = False
    address_bp = False
    if ":" in location:
        source_bp = True
    elif location.startswith("0x"):
        address_bp = True

    breakpoints = get_breakpoint_list()
    if not len(breakpoints):
        return None
    bps = []
    for bp in breakpoints:
        if source_bp:
            if bp["location"].endswith(location):
                bps.append(bp)
        elif address_bp:
            if bp["address"] == location:
                bps.append(bp)
        else:
            if bp["function"] == location:
                bps.append(bp)
    if len(bps):
        if single:
            return bps[0]
        return bps
    return None


def delete_breakpoint(bp):
    log.debug(f'deleting breakpoint {bp["id"]}')
    gdb.execute(f'd br {bp["id"]}')


def delete_breakpoints(bps):
    for bp in bps:
        delete_breakpoint(bp)


def clear_existing_breakpoints(name):
    """TODO: Docstring for clear_existing_breakpoints.
    :returns: TODO

    """

    bps = find_existing_breakpoints(name)
    if bps:
        delete_breakpoints(bps)