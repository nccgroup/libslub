import logging

# https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility
def trace(self, message, *args, **kws):
    if self.isEnabledFor(logging.TRACE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(logging.TRACE, message, args, **kws) 

class MyFormatter(logging.Formatter):
    """Defines how we format logs in stdout and files
    """

    # We use the TRACE level to check loaded files in gdb after reloading the script
    # so is mainly useful during development
    logging.TRACE = 5
    logging.addLevelName(logging.TRACE, 'TRACE')
    logging.Logger.trace = trace

    FORMATS = {
        logging.ERROR: "(%(asctime)s) [!] %(msg)s",
        logging.WARNING: "(%(asctime)s) WARNING: %(msg)s",
        logging.INFO: "(%(asctime)s) [*] %(msg)s",
        logging.DEBUG: "(%(asctime)s) DBG: %(msg)s",
        logging.TRACE: "(%(asctime)s) TRACE: %(msg)s",
        "DEFAULT": "%(asctime)s - %(msg)s"
    }

    def format(self, record):
        """Hooked Formatter.format() method to modify its behaviour
        """

        format_orig = self._style._fmt

        self._style._fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
        result = logging.Formatter.format(self, record)

        self._style._fmt = format_orig

        return result