import argparse
import logging
import struct
import sys
import traceback
from functools import wraps

import gdb

log = logging.getLogger("libslub")


class Options:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def show_last_exception():
    """Taken from gef. Let us see proper backtraces from python exceptions"""

    PYTHON_MAJOR = sys.version_info[0]
    horizontal_line = "-"
    right_arrow = "->"
    down_arrow = "\\->"

    print("")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print(" Exception raised ".center(80, horizontal_line))
    print("{}: {}".format(exc_type.__name__, exc_value))
    print(" Detailed stacktrace ".center(80, horizontal_line))
    for fs in traceback.extract_tb(exc_traceback)[::-1]:
        if PYTHON_MAJOR == 2:
            filename, lineno, method, code = fs
        else:
            try:
                filename, lineno, method, code = (
                    fs.filename,
                    fs.lineno,
                    fs.name,
                    fs.line,
                )
            except Exception:
                filename, lineno, method, code = fs

        print(
            """{} File "{}", line {:d}, in {}()""".format(
                down_arrow, filename, lineno, method
            )
        )
        print("   {}    {}".format(right_arrow, code))


# TODO: Is their no python built in for this?
def is_ascii(s):
    return all(c < 128 and c > 1 for c in s)


def hms_string(sec_elapsed):
    h = int(sec_elapsed / (60 * 60))
    m = int((sec_elapsed % (60 * 60)) / 60)
    s = int(sec_elapsed % 60)
    if h == 0:
        if m == 0:
            return "{:>02}s".format(s)
        else:
            return "{:>02}m{:>02}s".format(m, s)
    else:
        return "{}h{:>02}m{:>02}s".format(h, m, s)


# https://stackoverflow.com/questions/2556108/rreplace-how-to-replace-the-last-occurrence-of-an-expression-in-a-string
def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)


def prepare_list(L):
    return rreplace(", ".join([str(x) for x in L]), ",", " or", 1)


def string_to_int(num):
    """Convert an integer or hex integer string to an int
    :returns: converted integer

    especially helpful for using ArgumentParser()
    """
    if num.find("0x") != -1:
        return int(num, 16)
    else:
        return int(num)


def catch_exceptions(f):
    "Decorator to catch exceptions"

    @wraps(f)
    def _catch_exceptions(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            show_last_exception()

    return _catch_exceptions


def check_positive(value):
    try:
        ivalue = int(value)
    except Exception:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue


def check_count_value(value):
    if value == "unlimited":
        return None  # unlimited
    try:
        ivalue = int(value)
    except Exception:
        raise argparse.ArgumentTypeError("%s is an invalid int value" % value)
    if ivalue == 0:
        return None  # unlimited

    return ivalue


def check_count_value_positive(value):
    if value == "unlimited":
        return None  # unlimited
    try:
        ivalue = int(value)
    except Exception:
        raise argparse.ArgumentTypeError("%s is an invalid int value" % value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError("%s needs to be positive int value" % value)
    if ivalue == 0:
        return None  # unlimited

    return ivalue


hexdump_units = [1, 2, 4, 8, "dps"]


def check_hexdump_unit(value):
    """Especially helpful for using ArgumentParser()"""
    if value == "dps":
        return value

    try:
        ivalue = int(value)
    except Exception:
        raise argparse.ArgumentTypeError("%s is not a valid hexdump unit" % value)
    if ivalue not in hexdump_units:
        raise argparse.ArgumentTypeError("%s is not a valid hexdump unit" % value)
    return ivalue


def swap64(i):
    return struct.unpack("<Q", struct.pack(">Q", i))[0]


# TODO - This should go through the debugger abstraction
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
        except Exception:
            try:
                float(num)
                # multiple breakpoint detected
            except Exception:
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


def print_subparser_help(parser):
    # retrieve subparsers from parser
    subparsers_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]

    for subparsers_action in subparsers_actions:
        # get all subparsers and print help
        for choice, subparser in subparsers_action.choices.items():
            print(subparser.format_help())


def get_backtrace():
    d = {}
    output = gdb.execute("backtrace", to_string=True)
    d["raw"] = output
    funcs = []
    lines = output.split("\n")
    for i in range(len(lines)):
        # This is shown when "set verbose on" was executed so skip those
        if "Reading in symbols" in lines[i]:
            continue
        else:
            lines = lines[i:]
            break
    if lines[0].startswith("#0"):
        for line in lines:
            if not line:
                continue
            elts = line.split()
            if len(elts) < 3:
                # pu.print_error("Skipping too small line in backtrace")
                continue
            if not elts[0].startswith("#"):
                # pu.print_error("Skipping non-valid line in backtrace")
                continue
            if elts[2] == "in":
                # Something like:
                # #1  0x00007f834a8c8190 in _nl_make_l10nflist (l10nfile_list=...) at ../intl/l10nflist.c:237
                funcs.append(elts[3])
            else:
                # Something like:
                # #0  __GI___libc_free (mem=...) at malloc.c:3096
                funcs.append(elts[1])

    d["funcs"] = funcs
    return d


def print_hexdump_chunk(sb, o, maxlen=0, off=0, debug=False, unit=8, verbose=1):
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

    sb.dbg.print_hexdump(address, shown_size, unit=unit)
