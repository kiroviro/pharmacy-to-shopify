"""Tests for src/common/log_config.py"""

import logging
import sys

from src.common.log_config import setup_logging


class TestSetupLogging:
    def teardown_method(self):
        """Reset logger between tests."""
        logger = logging.getLogger("src")
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)

    def test_default_level_is_info(self):
        setup_logging()
        logger = logging.getLogger("src")
        assert logger.level == logging.INFO

    def test_verbose_sets_debug(self):
        setup_logging(verbose=True)
        logger = logging.getLogger("src")
        assert logger.level == logging.DEBUG

    def test_quiet_sets_warning(self):
        setup_logging(quiet=True)
        logger = logging.getLogger("src")
        assert logger.level == logging.WARNING

    def test_handler_outputs_to_stderr(self):
        setup_logging()
        logger = logging.getLogger("src")
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert handler.stream is sys.stderr
