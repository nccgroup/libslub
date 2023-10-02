import logging

log = logging.getLogger("libslub")
log.trace("frontend_gdb.py")

import libslub.frontend.commands.gdb.sbbreak as sbbreak
import libslub.frontend.commands.gdb.sbcache as sbcache
import libslub.frontend.commands.gdb.sbcrosscache as sbcrosscache
import libslub.frontend.commands.gdb.sbhelp as sbhelp
import libslub.frontend.commands.gdb.sblist as sblist
import libslub.frontend.commands.gdb.sbmeta as sbmeta
import libslub.frontend.commands.gdb.sbobject as sbobject
import libslub.frontend.commands.gdb.sbslabdb as sbslabdb
import libslub.frontend.commands.gdb.sbtrace as sbtrace
import libslub.frontend.commands.gdb.sbwatch as sbwatch


class frontend_gdb:
    """Register commands with GDB"""

    def __init__(self, sb):
        sbcache.sbcache(sb)
        sbobject.sbobject(sb)
        sblist.sblist(sb)
        sbmeta.sbmeta(sb)
        sbslabdb.sbslabdb(sb)
        sbcrosscache.sbcrosscache(sb)
        sbbreak.sbbreak(sb)
        sbtrace.sbtrace(sb)
        sbwatch.sbwatch(sb)
        sbhelp.sbhelp(sb)
