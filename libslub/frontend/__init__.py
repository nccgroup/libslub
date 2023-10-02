import logging
import sys

import libslub.logger as logger

# Setup here because isort will mess with initialization order, so we can't rely
# on the old manual initialization
# TODO: May even be nicer to move this logging setup somewhere else like libslub.debugger
try:
    log
except Exception:
    log = logging.getLogger("libslub")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logger.MyFormatter(datefmt="%H:%M:%S"))
    log.addHandler(handler)

log = logging.getLogger("libslub")
log.trace("libslub/frontend/__init__.py")
