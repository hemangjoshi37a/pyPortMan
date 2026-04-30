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
from .config import (
    ConfigManager,
    PyPortManConfig,
    BrokerConfig,
    LoggingConfig,
    SecurityConfig,
    AlertConfig,
    Environment,
    get_config_manager,
    get_config,
    reload_config
)
from .async_support import (
    AsyncHTTPClient,
    AsyncRequest,
    AsyncResponse,
    AsyncRateLimiter,
    AsyncBatchProcessor,
    run_async,
    run_async_sync
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
    'with_error_handling',
    'ConfigManager',
    'PyPortManConfig',
    'BrokerConfig',
    'LoggingConfig',
    'SecurityConfig',
    'AlertConfig',
    'Environment',
    'get_config_manager',
    'get_config',
    'reload_config',
    'AsyncHTTPClient',
    'AsyncRequest',
    'AsyncResponse',
    'AsyncRateLimiter',
    'AsyncBatchProcessor',
    'run_async',
    'run_async_sync'
]
