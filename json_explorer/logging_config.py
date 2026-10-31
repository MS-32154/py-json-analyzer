"""Logging setup for json_explorer.

As a library, json_explorer only attaches a ``NullHandler``: it never prints
log records unless the application configures logging. Records propagate to
the root logger, so ``logging.basicConfig(...)`` in an application works as
usual.

The CLI (and any application that wants json_explorer's own format) calls
:func:`configure_logging`, which attaches handlers to the package logger.
"""

import logging
import sys
from pathlib import Path
from typing import Literal

PACKAGE_LOGGER_NAME = "json_explorer"

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Package root logger: silent by default (library best practice).
logger = logging.getLogger(PACKAGE_LOGGER_NAME)
logger.addHandler(logging.NullHandler())


def configure_logging(
    level: LogLevel = "INFO",
    log_file: Path | None = None,
    format_string: str | None = None,
) -> None:
    """Send json_explorer log records to stderr (and optionally a file).

    Intended for the CLI and for applications that want json_explorer's own
    log output. Calling it again replaces the previous configuration.

    Args:
        level: Minimum level to emit (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file to write logs to, in addition to stderr.
        format_string: Custom format string for log messages.
    """
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        if not isinstance(handler, logging.NullHandler):
            handler.close()

    logger.setLevel(level)
    # These handlers own the output now; don't also pass records to root.
    logger.propagate = False

    formatter = logging.Formatter(format_string or DEFAULT_FORMAT)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger inside the json_explorer namespace.

    Pass ``__name__``. Names that already belong to the package are used as
    is; anything else is nested under ``json_explorer.``.
    """
    if name == PACKAGE_LOGGER_NAME or name.startswith(f"{PACKAGE_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{PACKAGE_LOGGER_NAME}.{name}")
