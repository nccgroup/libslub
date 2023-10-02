import argparse
import logging

import libslub.commands.breaks as cmd_break
import libslub.commands.cache as cmd_cache
import libslub.commands.crosscache as cmd_crosscache
import libslub.commands.db as cmd_db
import libslub.commands.list as cmd_list
import libslub.commands.meta as cmd_meta
import libslub.commands.object as cmd_object
import libslub.commands.trace as cmd_trace
import libslub.commands.watch as cmd_watch

log = logging.getLogger("libslub")
log.trace("help.py")


def generate_parser():
    parser = argparse.ArgumentParser(description="""List all libslub commands""")
    return parser


def slub_help(sb):
    """Print the usage of all libslub commands exposed to debuggers"""

    command_list = [
        cmd_break,
        cmd_cache,
        cmd_crosscache,
        cmd_list,
        cmd_meta,
        cmd_object,
        cmd_db,
        cmd_trace,
        cmd_watch,
    ]
    for cmd in command_list:
        name = cmd.__name__.split(".")[-1]
        # This is a work around because break is a reserved keyword
        if name == "breaks":
            name = "break"
        elif name == "db":
            name = "slabdb"

        print("{:<20}".format("sb" + name), end="")
        if name in "object":
            desc = cmd.generate_parser("sbobject").description.split("\n")[0]
        else:
            desc = cmd.generate_parser().description.split("\n")[0]
        print(desc)

    print("Note: Use a command name with -h to get additional help")
