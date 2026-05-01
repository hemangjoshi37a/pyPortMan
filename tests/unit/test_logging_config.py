"""Unit tests for logging_config module"""

import os
import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.logging_config import PyPortManLogger, get_logger


class TestPyPortManLogger:
    """Test PyPortManLogger class"""

    @pytest.fixture
    def clean_logs(self, tmp_path):
        """Clean logs directory"""
        logs_dir = tmp_path / "logs"
        with patch.object(PyPortManLogger, '_log_dir', logs_dir):
            yield logs_dir

    def test_get_logger_creates_new(self, clean_logs):
        """Test creating a new logger"""
        logger = PyPortManLogger.get_logger('test_logger')
        assert logger is not None
        assert logger.name == 'test_logger'

    def test_get_logger_returns_cached(self, clean_logs):
        """Test returning cached logger"""
        logger1 = PyPortManLogger.get_logger('test_logger')
        logger2 = PyPortManLogger.get_logger('test_logger')
        assert logger1 is logger2

    def test_get_logger_with_level(self, clean_logs):
        """Test creating logger with specific level"""
        logger = PyPortManLogger.get_logger('test_logger', level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_set_log_level_updates_all(self, clean_logs):
        """Test setting log level updates all loggers"""
        logger1 = PyPortManLogger.get_logger('logger1')
        logger2 = PyPortManLogger.get_logger('logger2')

        PyPortManLogger.set_log_level(logging.WARNING)

        # Check that loggers were updated
        assert PyPortManLogger._loggers['logger1'].level == logging.WARNING
        assert PyPortManLogger._loggers['logger2'].level == logging.WARNING

    def test_log_file_creation(self, clean_logs):
        """Test that log file is created"""
        logger = PyPortManLogger.get_logger('test_logger')
        logger.info("Test message")

        # Check that log file exists
        log_files = list(clean_logs.glob("*.log"))
        assert len(log_files) > 0

    def test_log_format(self, clean_logs, caplog):
        """Test log format"""
        logger = PyPortManLogger.get_logger('test_logger')

        with caplog.at_level(logging.INFO):
            logger.info("Test message")

        assert len(caplog.records) > 0
        assert "Test message" in caplog.text


class TestGetLogger:
    """Test get_logger function"""

    def test_get_logger_function(self):
        """Test get_logger function"""
        logger = get_logger('test')
        assert logger is not None
        assert logger.name == 'test'

    def test_get_logger_default_level(self):
        """Test get_logger with default level"""
        logger = get_logger('test')
        # The level is set to INFO (20)
        assert logger.level == logging.INFO

    def test_get_logger_custom_level(self):
        """Test get_logger with custom level"""
        logger = get_logger('test', level=logging.DEBUG)
        assert logger.level == logging.DEBUG


class TestLogLevels:
    """Test different log levels"""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create test logger"""
        logs_dir = tmp_path / "logs"
        with patch.object(PyPortManLogger, '_log_dir', logs_dir):
            return PyPortManLogger.get_logger('test_logger')

    def test_debug_level(self, logger, caplog):
        """Test DEBUG level logging"""
        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
        assert "Debug message" in caplog.text

    def test_info_level(self, logger, caplog):
        """Test INFO level logging"""
        with caplog.at_level(logging.INFO):
            logger.info("Info message")
        assert "Info message" in caplog.text

    def test_warning_level(self, logger, caplog):
        """Test WARNING level logging"""
        with caplog.at_level(logging.WARNING):
            logger.warning("Warning message")
        assert "Warning message" in caplog.text

    def test_error_level(self, logger, caplog):
        """Test ERROR level logging"""
        with caplog.at_level(logging.ERROR):
            logger.error("Error message")
        assert "Error message" in caplog.text

    def test_critical_level(self, logger, caplog):
        """Test CRITICAL level logging"""
        with caplog.at_level(logging.CRITICAL):
            logger.critical("Critical message")
        assert "Critical message" in caplog.text


class TestLogRotation:
    """Test log rotation"""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create test logger"""
        logs_dir = tmp_path / "logs"
        with patch.object(PyPortManLogger, '_log_dir', logs_dir):
            return PyPortManLogger.get_logger('test_logger')

    def test_log_file_naming(self, logger):
        """Test log file naming convention"""
        logger.info("Test message")

        # Check file name format
        log_files = list(Path(logger.handlers[1].baseFilename).parent.glob("*.log"))
        assert len(log_files) > 0

        # File should be named pyportman_YYYYMMDD.log
        for log_file in log_files:
            assert log_file.name.startswith("pyportman_")
            assert log_file.name.endswith(".log")
