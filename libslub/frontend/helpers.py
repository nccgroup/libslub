import sys
import traceback
import argparse
import struct
from functools import wraps

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
            except:
                filename, lineno, method, code = fs

        print(
            """{} File "{}", line {:d}, in {}()""".format(
                down_arrow, filename, lineno, method
            )
        )
        print("   {}    {}".format(right_arrow, code))

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
    return rreplace(', '.join([str(x) for x in L]), ',', ' or', 1)

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
    except:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue

def check_count_value(value):
    if value == "unlimited":
        return None # unlimited
    try:
        ivalue = int(value)
    except:
        raise argparse.ArgumentTypeError("%s is an invalid int value" % value)
    if ivalue == 0:
        return None # unlimited

    return ivalue

def check_count_value_positive(value):
    if value == "unlimited":
        return None # unlimited
    try:
        ivalue = int(value)
    except:
        raise argparse.ArgumentTypeError("%s is an invalid int value" % value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError("%s needs to be positive int value" % value)
    if ivalue == 0:
        return None # unlimited

    return ivalue


hexdump_units = [1, 2, 4, 8, "dps"]
def check_hexdump_unit(value):
    """Especially helpful for using ArgumentParser()
    """
    if value == "dps":
        return value
    
    try:
        ivalue = int(value)
    except:
        raise argparse.ArgumentTypeError("%s is not a valid hexdump unit" % value)
    if ivalue not in hexdump_units:
        raise argparse.ArgumentTypeError("%s is not a valid hexdump unit" % value)
    return ivalue


def swap64(i):
    return struct.unpack("<Q", struct.pack(">Q", i))[0]