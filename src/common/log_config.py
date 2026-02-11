"""
Logging Configuration

Configures structured logging for the application.
Output goes to stderr to keep stdout clean for user-facing reports.
"""

import logging
import sys


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Configure logging for the application.

    Args:
        verbose: If True, set level to DEBUG
        quiet: If True, set level to WARNING
    """
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))

    logger = logging.getLogger("src")
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    logger.handlers.clear()
    logger.addHandler(handler)
