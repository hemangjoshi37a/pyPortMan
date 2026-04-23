"""
Core Module for pyPortMan
Contains core functionality for client management, orders, portfolio tracking, and market data
"""

from .logging_config import get_logger, PyPortManLogger
from .error_handler import (
    PyPortManError,
    AuthenticationError,
    OrderError,
    MarketDataError,
    PortfolioError,
    RateLimitError,
    ValidationError,
    retry_on_failure,
    with_error_handling
)

__all__ = [
    'get_logger',
    'PyPortManLogger',
    'PyPortManError',
    'AuthenticationError',
    'OrderError',
    'MarketDataError',
    'PortfolioError',
    'RateLimitError',
    'ValidationError',
    'retry_on_failure',
    'with_error_handling'
]
