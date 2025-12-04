"""Centralized logging configuration for json_explorer.

This module provides a single point of configuration for all logging
throughout the json_explorer package.
"""

import logging
import sys
from pathlib import Path
from typing import Literal

# Module-level logger that can be used by other modules
logger = logging.getLogger("json_explorer")

# Prevent duplicate log messages
logger.propagate = False

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def configure_logging(
    level: LogLevel = "INFO",
    log_file: Path | None = None,
    format_string: str | None = None,
) -> None:
    """Configure logging for the json_explorer package.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path to write logs to.
        format_string: Custom format string for log messages.
    """
    # Clear existing handlers to prevent duplicates
    logger.handlers.clear()

    # Set the logger level
    logger.setLevel(getattr(logging, level))

    # Default format if none provided
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file is not None:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Name of the module (typically __name__).

    Returns:
        Logger instance configured with the package settings.
    """
    return logging.getLogger(f"json_explorer.{name}")


# Configure with defaults on import
configure_logging()
