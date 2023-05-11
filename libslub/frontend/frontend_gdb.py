import logging
import importlib

log = logging.getLogger("libslub")
log.trace(f"frontend_gdb.py")

import libslub.frontend.commands.gdb.sbhelp as sbhelp
importlib.reload(sbhelp)
import libslub.frontend.commands.gdb.sbbreak as sbbreak
importlib.reload(sbbreak)
import libslub.frontend.commands.gdb.sblist as sblist
importlib.reload(sblist)
import libslub.frontend.commands.gdb.sbtrace as sbtrace
importlib.reload(sbtrace)
import libslub.frontend.commands.gdb.sbwatch as sbwatch
importlib.reload(sbwatch)
import libslub.frontend.commands.gdb.sbcrosscache as sbcrosscache
importlib.reload(sbcrosscache)
import libslub.frontend.commands.gdb.sbmeta as sbmeta
importlib.reload(sbmeta)
import libslub.frontend.commands.gdb.sbcache as sbcache
importlib.reload(sbcache)
import libslub.frontend.commands.gdb.sbslabdb as sbslabdb
importlib.reload(sbslabdb)
import libslub.frontend.commands.gdb.sbobject as sbobject
importlib.reload(sbobject)

class frontend_gdb:
    """Register commands with GDB"""

    def __init__(self, sb):

        # We share slab among all commands below

        # The below dictates in what order they will be shown in gdb
        cmds = []
        cmds.append(sbcache.sbcache(sb))
        cmds.append(sbobject.sbobject(sb))
        cmds.append(sblist.sblist(sb))
        cmds.append(sbmeta.sbmeta(sb))
        cmds.append(sbslabdb.sbslabdb(sb))
        cmds.append(sbcrosscache.sbcrosscache(sb))

        if sb.breakpoints_enabled:
            cmds.append(sbbreak.sbbreak(sb))
            cmds.append(sbtrace.sbtrace(sb))
            cmds.append(sbwatch.sbwatch(sb))

        sbhelp.sbhelp(sb, cmds)
