# pyPortMan Testing Guide

This guide explains how to run and write tests for pyPortMan.

## Installation

Install testing dependencies:

```bash
pip install -r requirements_testing.txt
```

Or install all dependencies including testing:

```bash
pip install -r requirements_new.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest -m unit
```

### Run Integration Tests Only

```bash
pytest -m integration
```

### Run Tests with Coverage

```bash
pytest --cov=core --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`.

### Run Specific Test File

```bash
pytest tests/unit/test_error_handler.py
```

### Run Specific Test Function

```bash
pytest tests/unit/test_error_handler.py::TestRateLimiter::test_rate_limiter_initialization
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Tests in Parallel (requires pytest-xdist)

```bash
pytest -n auto
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_client.py             # BrokerClient tests
│   ├── test_orders.py             # OrderManager tests
│   ├── test_portfolio.py          # PortfolioManager tests
│   ├── test_market_data.py        # MarketDataManager tests
│   ├── test_error_handler.py      # Error handling tests
│   ├── test_security.py           # Security tests
│   └── test_logging_config.py     # Logging tests
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_zerodha_integration.py
│   ├── test_angel_integration.py
│   └── test_multi_broker.py
└── fixtures/                      # Test fixtures
    ├── __init__.py
    ├── sample_orders.py
    ├── sample_holdings.py
    └── sample_market_data.py
```

## Writing Tests

### Unit Tests

Unit tests should mock all external dependencies:

```python
import pytest
from unittest.mock import Mock
from core.orders import OrderManager

def test_place_order():
    # Create mock client
    client = Mock()
    client.broker = 'zerodha'
    client._authenticated = True

    # Create order manager
    order_manager = OrderManager(client)

    # Mock API response
    order_manager.client.api = Mock()
    order_manager.client.api.place_order.return_value = {
        'order_id': 'ORD123456',
        'status': 'OPEN'
    }

    # Test
    order = order_manager.place_order(
        symbol='RELIANCE',
        exchange='NSE',
        transaction_type=TransactionType.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        price=2500.0,
        product=ProductType.CNC
    )

    assert order.order_id == 'ORD123456'
    assert order.status == OrderStatus.PENDING
```

### Integration Tests

Integration tests use real broker APIs (marked with `@pytest.mark.integration`):

```python
import pytest

@pytest.mark.integration
@pytest.mark.requires_api
class TestZerodhaIntegration:
    def test_zerodha_login(self, zerodha_client):
        assert zerodha_client.is_authenticated() is True
```

### Using Fixtures

Fixtures are defined in `conftest.py`:

```python
def test_with_fixture(sample_order_data):
    assert sample_order_data['symbol'] == 'RELIANCE'
```

## Test Markers

- `unit`: Unit tests (mocked dependencies)
- `integration`: Integration tests (real APIs)
- `slow`: Slow running tests
- `requires_api`: Tests requiring real API credentials

## Environment Variables for Integration Tests

For integration tests, set these environment variables:

```bash
# Zerodha
export ZERODHA_USER_ID="your_user_id"
export ZERODHA_PASSWORD="your_password"
export ZERODHA_API_KEY="your_api_key"
export ZERODHA_TOTP_KEY="your_totp_key"
export ZERODHA_TOTP_ENABLED="1"

# Angel
export ANGEL_USER_ID="your_user_id"
export ANGEL_PASSWORD="your_password"
export ANGEL_API_KEY="your_api_key"
export ANGEL_CLIENT_ID="your_client_id"
```

Or create a `.env.test` file:

```env
ZERODHA_USER_ID=your_user_id
ZERODHA_PASSWORD=your_password
ZERODHA_API_KEY=your_api_key
ZERODHA_TOTP_KEY=your_totp_key
ZERODHA_TOTP_ENABLED=1
```

## Coverage Target

Target coverage: 80% for core modules.

To check coverage:

```bash
pytest --cov=core --cov-report=term-missing
```

## Continuous Integration

Tests are configured to run with:

- pytest for test execution
- pytest-cov for coverage reporting
- pytest-mock for mocking

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running from the project root:

```bash
cd /path/to/pyPortMan
pytest
```

### Missing Dependencies

Install testing dependencies:

```bash
pip install -r requirements_testing.txt
```

### Integration Tests Failing

Integration tests require valid broker credentials. Make sure environment variables are set or skip integration tests:

```bash
pytest -m "not integration"
```

## Best Practices

1. **Mock external dependencies** in unit tests
2. **Use descriptive test names** that explain what is being tested
3. **Arrange-Act-Assert pattern** for test structure
4. **One assertion per test** when possible
5. **Use fixtures** for common test data
6. **Keep tests independent** - they should run in any order
7. **Test edge cases** - empty inputs, invalid values, etc.
8. **Test error conditions** - exceptions, error messages

## Example Test Template

```python
import pytest
from unittest.mock import Mock
from core.module import ClassToTest

class TestClassToTest:
    """Test ClassToTest"""

    @pytest.fixture
    def mock_dependency(self):
        """Create mock dependency"""
        mock = Mock()
        mock.method.return_value = "expected_value"
        return mock

    @pytest.fixture
    def instance(self, mock_dependency):
        """Create instance with mock dependency"""
        return ClassToTest(mock_dependency)

    def test_method_success(self, instance):
        """Test successful method call"""
        result = instance.method()
        assert result == "expected_value"

    def test_method_failure(self, instance):
        """Test method failure"""
        instance.dependency.method.side_effect = Exception("Error")
        with pytest.raises(Exception):
            instance.method()
```

## Contributing Tests

When adding new features, please:

1. Write unit tests for all new functions/classes
2. Update existing tests if behavior changes
3. Ensure coverage remains above 80%
4. Add integration tests if the feature interacts with external APIs
5. Update this README if adding new test patterns
