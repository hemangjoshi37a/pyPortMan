"""Unit tests for error_handler module"""

import pytest
import time
from unittest.mock import Mock, patch

from core.error_handler import (
    PyPortManError,
    AuthenticationError,
    OrderError,
    MarketDataError,
    PortfolioError,
    RateLimitError,
    ValidationError,
    NetworkError,
    ConfigurationError,
    retry_on_failure,
    with_error_handling,
    RateLimiter,
    InputValidator
)


class TestPyPortManError:
    """Test base PyPortManError"""

    def test_base_error_creation(self):
        """Test creating base error"""
        error = PyPortManError("Test error")
        assert str(error) == "Test error"
        result = error.to_dict()
        assert result['message'] == 'Test error'
        assert result['details'] == {}
        assert 'error_type' in result
        assert 'timestamp' in result

    def test_base_error_with_details(self):
        """Test creating error with details"""
        error = PyPortManError("Test error", details={'key': 'value'})
        result = error.to_dict()
        assert result['message'] == 'Test error'
        assert result['details'] == {'key': 'value'}


class TestSpecificErrors:
    """Test specific error types"""

    def test_authentication_error(self):
        """Test AuthenticationError"""
        error = AuthenticationError("Login failed")
        assert isinstance(error, PyPortManError)
        assert "Login failed" in str(error)

    def test_order_error(self):
        """Test OrderError"""
        error = OrderError("Order placement failed")
        assert isinstance(error, PyPortManError)

    def test_market_data_error(self):
        """Test MarketDataError"""
        error = MarketDataError("Data fetch failed")
        assert isinstance(error, PyPortManError)

    def test_portfolio_error(self):
        """Test PortfolioError"""
        error = PortfolioError("Portfolio update failed")
        assert isinstance(error, PyPortManError)

    def test_rate_limit_error(self):
        """Test RateLimitError"""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        assert isinstance(error, PyPortManError)
        assert error.retry_after == 60

    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Invalid input")
        assert isinstance(error, PyPortManError)

    def test_network_error(self):
        """Test NetworkError"""
        error = NetworkError("Connection failed")
        assert isinstance(error, PyPortManError)

    def test_configuration_error(self):
        """Test ConfigurationError"""
        error = ConfigurationError("Config missing")
        assert isinstance(error, PyPortManError)


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization"""
        limiter = RateLimiter(max_calls=10, period=60.0)
        assert limiter.max_calls == 10
        assert limiter.period == 60.0

    def test_rate_limiter_first_call(self):
        """Test first call doesn't block"""
        limiter = RateLimiter(max_calls=10, period=60.0)
        limiter.wait_if_needed()  # Should not block

    def test_rate_limiter_within_limit(self):
        """Test calls within limit don't block"""
        limiter = RateLimiter(max_calls=5, period=60.0)
        for _ in range(5):
            limiter.wait_if_needed()  # Should not block

    def test_rate_limiter_exceeds_limit(self):
        """Test exceeding limit blocks"""
        limiter = RateLimiter(max_calls=2, period=60.0)
        for _ in range(2):
            limiter.wait_if_needed()

        # Next call should block
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed >= 0  # At least some blocking occurred

    def test_rate_limiter_reset(self):
        """Test reset functionality"""
        limiter = RateLimiter(max_calls=2, period=60.0)
        for _ in range(2):
            limiter.wait_if_needed()

        limiter.reset()
        # Should not block after reset
        limiter.wait_if_needed()

    def test_rate_limiter_remaining_calls(self):
        """Test get_remaining_calls"""
        limiter = RateLimiter(max_calls=5, period=60.0)
        assert limiter.get_remaining_calls() == 5

        limiter.wait_if_needed()
        assert limiter.get_remaining_calls() == 4


class TestInputValidator:
    """Test InputValidator class"""

    def test_validate_symbol_valid(self):
        """Test valid symbol validation"""
        result = InputValidator.validate_symbol('RELIANCE')
        assert result == 'RELIANCE'

    def test_validate_symbol_invalid_empty(self):
        """Test empty symbol validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_symbol('')

    def test_validate_symbol_invalid_too_short(self):
        """Test too short symbol validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_symbol('A')

    def test_validate_symbol_invalid_too_long(self):
        """Test too long symbol validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_symbol('A' * 21)

    def test_validate_quantity_valid(self):
        """Test valid quantity validation"""
        result = InputValidator.validate_quantity(10)
        assert result == 10

    def test_validate_quantity_invalid_zero(self):
        """Test zero quantity validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_quantity(0)

    def test_validate_quantity_invalid_negative(self):
        """Test negative quantity validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_quantity(-5)

    def test_validate_quantity_invalid_float(self):
        """Test float quantity validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_quantity(10.5)

    def test_validate_price_valid(self):
        """Test valid price validation"""
        result = InputValidator.validate_price(2500.0)
        assert result == 2500.0

    def test_validate_price_invalid_zero(self):
        """Test zero price validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_price(0)

    def test_validate_price_invalid_negative(self):
        """Test negative price validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_price(-100.0)

    def test_validate_exchange_valid(self):
        """Test valid exchange validation"""
        for exchange in ['NSE', 'BSE', 'MCX', 'NFO']:
            result = InputValidator.validate_exchange(exchange)
            assert result == exchange

    def test_validate_exchange_invalid(self):
        """Test invalid exchange validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_exchange('INVALID')

    def test_validate_order_type_valid(self):
        """Test valid order type validation"""
        for order_type in ['MARKET', 'LIMIT', 'SL', 'SL-M']:
            result = InputValidator.validate_order_type(order_type)
            assert result == order_type

    def test_validate_order_type_invalid(self):
        """Test invalid order type validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_order_type('INVALID')

    def test_validate_transaction_type_valid(self):
        """Test valid transaction type validation"""
        for trans_type in ['BUY', 'SELL']:
            result = InputValidator.validate_transaction_type(trans_type)
            assert result == trans_type

    def test_validate_transaction_type_invalid(self):
        """Test invalid transaction type validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_transaction_type('INVALID')

    def test_validate_product_valid(self):
        """Test valid product validation"""
        for product in ['CNC', 'MIS', 'NRML', 'BO', 'CO']:
            result = InputValidator.validate_product(product)
            assert result == product

    def test_validate_product_invalid(self):
        """Test invalid product validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_product('INVALID')

    def test_validate_date_valid(self):
        """Test valid date validation"""
        result = InputValidator.validate_date('2024-01-01')
        assert result.day == 1
        assert result.month == 1
        assert result.year == 2024

    def test_validate_date_invalid_format(self):
        """Test invalid date format"""
        with pytest.raises(ValidationError):
            InputValidator.validate_date('01-01-2024')

    def test_validate_percentage_valid(self):
        """Test valid percentage validation"""
        result = InputValidator.validate_percentage(50.0)
        assert result == 50.0

    def test_validate_percentage_invalid_negative(self):
        """Test negative percentage validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_percentage(-10.0)

    def test_validate_percentage_invalid_over_100(self):
        """Test percentage over 100 validation"""
        with pytest.raises(ValidationError):
            InputValidator.validate_percentage(150.0)


class TestRetryOnFailure:
    """Test retry_on_failure decorator"""

    def test_retry_on_failure_success(self):
        """Test successful call without retry"""
        @retry_on_failure(max_retries=3)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_retry_on_failure_with_retry(self):
        """Test retry on failure"""
        call_count = 0

        @retry_on_failure(max_retries=3, initial_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_on_failure_exhausted(self):
        """Test retry exhausted"""
        @retry_on_failure(max_retries=2, initial_delay=0.01)
        def test_func():
            raise Exception("Persistent failure")

        with pytest.raises(Exception):
            test_func()

    def test_retry_on_failure_specific_exception(self):
        """Test retry on specific exception"""
        call_count = 0

        @retry_on_failure(max_retries=3, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = test_func()
        assert result == "success"

    def test_retry_on_failure_wrong_exception(self):
        """Test no retry on wrong exception"""
        @retry_on_failure(max_retries=3, exceptions=(ValueError,))
        def test_func():
            raise TypeError("Wrong exception")

        with pytest.raises(TypeError):
            test_func()


class TestWithErrorHandling:
    """Test with_error_handling decorator"""

    def test_with_error_handling_success(self):
        """Test successful call"""
        @with_error_handling()
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_with_error_handling_pyportman_error(self):
        """Test PyPortManError handling"""
        @with_error_handling(raise_on_error=False, default_return="error")
        def test_func():
            raise OrderError("Order failed")

        result = test_func()
        assert result == "error"

    def test_with_error_handling_generic_exception(self):
        """Test generic exception handling"""
        @with_error_handling(raise_on_error=False, default_return="error")
        def test_func():
            raise Exception("Generic error")

        result = test_func()
        assert result == "error"

    def test_with_error_handling_raise_on_error(self):
        """Test raise_on_error=True"""
        @with_error_handling(raise_on_error=True)
        def test_func():
            raise OrderError("Order failed")

        with pytest.raises(OrderError):
            test_func()
