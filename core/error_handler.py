"""
Error Handling Module
Custom exceptions and retry logic for pyPortMan
"""

import time
import functools
import logging
from typing import Callable, Type, Tuple, Optional, Any
from datetime import datetime, timedelta


# Custom Exceptions
class PyPortManError(Exception):
    """Base exception for all pyPortMan errors"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/API responses"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'timestamp': datetime.now().isoformat()
        }


class AuthenticationError(PyPortManError):
    """Raised when authentication fails"""
    pass


class OrderError(PyPortManError):
    """Raised when order placement/modification/cancellation fails"""
    pass


class MarketDataError(PyPortManError):
    """Raised when market data fetching fails"""
    pass


class PortfolioError(PyPortManError):
    """Raised when portfolio operations fail"""
    pass


class RateLimitError(PyPortManError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(PyPortManError):
    """Raised when input validation fails"""
    pass


class NetworkError(PyPortManError):
    """Raised when network operations fail"""
    pass


class ConfigurationError(PyPortManError):
    """Raised when configuration is invalid"""
    pass


# Retry Decorator
def retry_on_failure(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    Decorator to retry a function on failure with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry on
        logger: Logger instance for logging retry attempts

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        if logger:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries} retries. "
                                f"Final error: {str(e)}"
                            )
                        raise

                    if logger:
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retrying in {delay:.2f}s. Error: {str(e)}"
                        )

                    time.sleep(delay)
                    delay *= backoff_factor

            # This should never be reached, but just in case
            raise last_exception if last_exception else PyPortManError("Unknown error in retry")

        return wrapper
    return decorator


# Error Handling Decorator
def with_error_handling(
    logger: Optional[logging.Logger] = None,
    raise_on_error: bool = True,
    default_return: Any = None
) -> Callable:
    """
    Decorator to handle errors consistently across functions

    Args:
        logger: Logger instance for logging errors
        raise_on_error: Whether to raise exceptions or return default
        default_return: Value to return on error if not raising

    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except PyPortManError as e:
                if logger:
                    logger.error(f"Error in {func.__name__}: {e.message}", extra={'details': e.details})
                if raise_on_error:
                    raise
                return default_return
            except Exception as e:
                if logger:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                if raise_on_error:
                    raise PyPortManError(f"Unexpected error: {str(e)}")
                return default_return

        return wrapper
    return decorator


# Rate Limiter
class RateLimiter:
    """
    Simple rate limiter to prevent API rate limit violations

    Usage:
        limiter = RateLimiter(max_calls=10, period=60)  # 10 calls per 60 seconds
        limiter.wait_if_needed()  # Will block if rate limit exceeded
    """

    def __init__(self, max_calls: int = 10, period: float = 60.0):
        """
        Initialize rate limiter

        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self._lock = None  # Could use threading.Lock for thread safety

    def wait_if_needed(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Wait if rate limit would be exceeded

        Args:
            logger: Optional logger for logging rate limit events
        """
        now = datetime.now()

        # Remove calls older than the period
        self.calls = [call_time for call_time in self.calls
                     if now - call_time < timedelta(seconds=self.period)]

        if len(self.calls) >= self.max_calls:
            # Calculate wait time
            oldest_call = self.calls[0]
            wait_time = (oldest_call + timedelta(seconds=self.period) - now).total_seconds()

            if wait_time > 0:
                if logger:
                    logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)

        # Record this call
        self.calls.append(now)

    def reset(self) -> None:
        """Reset the rate limiter"""
        self.calls = []

    def get_remaining_calls(self) -> int:
        """Get number of remaining calls in current period"""
        now = datetime.now()
        self.calls = [call_time for call_time in self.calls
                     if now - call_time < timedelta(seconds=self.period)]
        return self.max_calls - len(self.calls)


# Input Validator
class InputValidator:
    """Input validation utilities"""

    @staticmethod
    def validate_symbol(symbol: str) -> str:
        """Validate stock symbol"""
        if not symbol or not isinstance(symbol, str):
            raise ValidationError("Symbol must be a non-empty string")
        symbol = symbol.strip().upper()
        if not symbol or len(symbol) < 2 or len(symbol) > 20:
            raise ValidationError("Symbol must be 2-20 characters long")
        return symbol

    @staticmethod
    def validate_quantity(quantity: int) -> int:
        """Validate order quantity"""
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError("Quantity must be a positive integer")
        return quantity

    @staticmethod
    def validate_price(price: float) -> float:
        """Validate price"""
        if not isinstance(price, (int, float)) or price <= 0:
            raise ValidationError("Price must be a positive number")
        return float(price)

    @staticmethod
    def validate_exchange(exchange: str) -> str:
        """Validate exchange"""
        valid_exchanges = ['NSE', 'BSE', 'MCX', 'NFO']
        exchange = exchange.strip().upper()
        if exchange not in valid_exchanges:
            raise ValidationError(f"Exchange must be one of: {', '.join(valid_exchanges)}")
        return exchange

    @staticmethod
    def validate_order_type(order_type: str) -> str:
        """Validate order type"""
        valid_types = ['MARKET', 'LIMIT', 'SL', 'SL-M']
        order_type = order_type.strip().upper()
        if order_type not in valid_types:
            raise ValidationError(f"Order type must be one of: {', '.join(valid_types)}")
        return order_type

    @staticmethod
    def validate_transaction_type(transaction_type: str) -> str:
        """Validate transaction type"""
        valid_types = ['BUY', 'SELL']
        transaction_type = transaction_type.strip().upper()
        if transaction_type not in valid_types:
            raise ValidationError(f"Transaction type must be one of: {', '.join(valid_types)}")
        return transaction_type

    @staticmethod
    def validate_product(product: str) -> str:
        """Validate product type"""
        valid_products = ['CNC', 'MIS', 'NRML', 'BO', 'CO']
        product = product.strip().upper()
        if product not in valid_products:
            raise ValidationError(f"Product must be one of: {', '.join(valid_products)}")
        return product

    @staticmethod
    def validate_date(date_str: str, date_format: str = '%Y-%m-%d') -> datetime:
        """Validate and parse date string"""
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            raise ValidationError(f"Date must be in format: {date_format}")

    @staticmethod
    def validate_percentage(percent: float) -> float:
        """Validate percentage value"""
        if not isinstance(percent, (int, float)) or percent < 0 or percent > 100:
            raise ValidationError("Percentage must be between 0 and 100")
        return float(percent)
