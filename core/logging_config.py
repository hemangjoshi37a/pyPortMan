"""
Logging Configuration Module
Provides centralized logging configuration for pyPortMan
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class PyPortManLogger:
    """Centralized logger for pyPortMan"""

    _loggers = {}
    _log_dir = Path(__file__).parent.parent / "logs"
    _log_dir.mkdir(exist_ok=True)

    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        """
        Get or create a logger with the specified name

        Args:
            name: Logger name (usually __name__)
            level: Logging level (default: INFO)

        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Console handler with formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for persistent logs
        log_file = cls._log_dir / f"pyportman_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def set_log_level(cls, level: int):
        """Set log level for all loggers"""
        for logger in cls._loggers.values():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Convenience function to get a logger

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    return PyPortManLogger.get_logger(name, level)


# Pre-configured loggers for different modules
broker_logger = get_logger('pyportman.broker', logging.INFO)
order_logger = get_logger('pyportman.orders', logging.INFO)
portfolio_logger = get_logger('pyportman.portfolio', logging.INFO)
market_logger = get_logger('pyportman.market', logging.INFO)
auth_logger = get_logger('pyportman.auth', logging.WARNING)  # Sensitive data
error_logger = get_logger('pyportman.errors', logging.ERROR)
