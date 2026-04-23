# pyPortMan Migration Guide

This guide helps you migrate from the old pyPortMan architecture to the new refactored version.

## Overview of Changes

The new architecture introduces:

1. **Modular Code Structure** - Split into core modules
2. **Enhanced Security** - `.env` based credentials with encryption
3. **Proper Error Handling** - Custom exceptions and retry logic
4. **Logging** - Structured logging instead of print statements
5. **Rate Limiting** - Built-in API rate limiting
6. **Input Validation** - Comprehensive validation for all inputs

## File Structure

### Old Structure
```
pyPortMan/
├── pyportmanlib.py (1385 lines)
├── auth_info.xlsx
├── stocks.xlsx
└── ...
```

### New Structure
```
pyPortMan/
├── core/
│   ├── __init__.py
│   ├── client.py          # Broker client management
│   ├── orders.py          # Order operations
│   ├── portfolio.py       # Portfolio tracking
│   ├── market_data.py     # Market data fetching
│   ├── error_handler.py   # Error handling & retry logic
│   ├── logging_config.py  # Logging configuration
│   └── security.py        # Security & credentials
├── pyportmanlib_new.py    # New main module
├── pyportmanlib.py        # Old module (backward compatible)
├── .env                   # Credentials (encrypted)
├── .env.example           # Example credentials file
└── requirements_new.txt   # Updated dependencies
```

## Migration Steps

### Step 1: Install New Dependencies

```bash
pip install -r requirements_new.txt
```

### Step 2: Set Up Environment Variables

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and add your credentials:
```bash
# Zerodha credentials
ZERODHA_MAIN_USER_ID=your_user_id
ZERODHA_MAIN_PASSWORD=your_password
ZERODHA_MAIN_PIN=your_pin
ZERODHA_MAIN_TOTP_KEY=your_totp_secret
ZERODHA_MAIN_TOTP_ENABLED=true

# Angel Broking credentials
ANGEL_ANGEL_MAIN_USER_ID=your_user_id
ANGEL_ANGEL_MAIN_PASSWORD=your_password
ANGEL_ANGEL_MAIN_API_KEY=your_api_key
```

3. Generate encryption key (optional but recommended):
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Add the generated key to `.env`:
```bash
PYPORTMAN_ENCRYPTION_KEY=your-generated-key
```

### Step 3: Update Your Code

#### Option A: Use Backward Compatible API (Recommended for Quick Migration)

The new `pyportmanlib_new.py` maintains backward compatibility with the old API:

```python
# Old code (still works)
from pyportmanlib import one_client_class, my_clients_group

# New code (same API)
from pyportmanlib_new import one_client_class, my_clients_group

# Usage remains the same
client = one_client_class(
    ac_broker='zerodha',
    ac_name='main',
    ac_id='user_id',
    ac_pass='password',
    ac_pin='pin',
    totp_key='totp_secret',
    totp_enabled=1
)
client.do_login()
```

#### Option B: Use New Architecture (Recommended for New Projects)

```python
from core.client import ClientManager, CredentialManager
from core.orders import OrderManager
from core.portfolio import PortfolioManager
from core.market_data import MarketDataManager

# Initialize credential manager
cred_manager = CredentialManager()

# Create client manager
client_manager = ClientManager(cred_manager)

# Add client (credentials loaded from .env)
client = client_manager.add_client('zerodha', 'main')

# Login
client.login()

# Create managers
order_manager = OrderManager(client)
portfolio_manager = PortfolioManager(client)
market_manager = MarketDataManager(client)

# Use the managers
holdings = portfolio_manager.get_holdings()
orders = order_manager.get_orders()
quote = market_manager.get_quote('RELIANCE')
```

### Step 4: Migrate Excel Credentials to .env

If you have credentials in `auth_info.xlsx`, migrate them to `.env`:

```python
# Migration script
import pandas as pd
from core.security import CredentialManager

# Read old credentials
df = pd.read_excel('auth_info.xlsx')

# For each row, add to .env
for _, row in df.iterrows():
    broker = row['ac_broker'].upper()
    name = row['ac_name'].upper()

    print(f"# {broker} {name}")
    print(f"{broker}_{name}_USER_ID={row['ac_id']}")
    print(f"{broker}_{name}_PASSWORD={row['ac_pass']}")
    print(f"{broker}_{name}_PIN={row['ac_pin']}")
    if 'api_key' in row:
        print(f"{broker}_{name}_API_KEY={row['api_key']}")
    if 'totp_key' in row:
        print(f"{broker}_{name}_TOTP_KEY={row['totp_key']}")
    print(f"{broker}_{name}_TOTP_ENABLED={row.get('totp_enabled', 0)}")
    print()
```

### Step 5: Update Error Handling

Old code:
```python
try:
    client.do_login()
except Exception as e:
    print(f"Error: {e}")
```

New code:
```python
from core.error_handler import AuthenticationError, PyPortManError

try:
    client.login()
except AuthenticationError as e:
    logger.error(f"Authentication failed: {e.message}")
except PyPortManError as e:
    logger.error(f"Error: {e.message}")
```

### Step 6: Update Logging

Old code:
```python
print("Login successful")
print(f"Order placed: {order_id}")
```

New code:
```python
from core.logging_config import get_logger

logger = get_logger('my_app')
logger.info("Login successful")
logger.info(f"Order placed: {order_id}")
```

## API Changes

### Client Initialization

**Old:**
```python
client = one_client_class(
    ac_broker='zerodha',
    ac_name='main',
    ac_id='user_id',
    ac_pass='password',
    ac_pin='pin',
    api_key='',
    totp_key='',
    totp_enabled=0
)
```

**New:**
```python
# Credentials loaded from .env
client = client_manager.add_client('zerodha', 'main')
```

### Order Placement

**Old:**
```python
result = client.place_order(
    symbol='RELIANCE',
    quantity=10,
    transaction_type='BUY',
    order_type='LIMIT',
    price=2500
)
```

**New:**
```python
order = order_manager.place_order(
    symbol='RELIANCE',
    quantity=10,
    transaction_type='BUY',
    order_type='LIMIT',
    price=2500
)
```

### Getting Holdings

**Old:**
```python
holdings = client.get_holdings_list()
for holding in holdings:
    print(holding.tradingsymbol, holding.pnl)
```

**New:**
```python
holdings = portfolio_manager.get_holdings()
for holding in holdings:
    print(holding.symbol, holding.pnl)
```

## New Features

### 1. Retry Logic

Automatic retry with exponential backoff:

```python
from core.error_handler import retry_on_failure

@retry_on_failure(max_retries=3, initial_delay=1.0)
def my_function():
    # This will retry up to 3 times on failure
    pass
```

### 2. Rate Limiting

Built-in rate limiting for API calls:

```python
from core.error_handler import RateLimiter

limiter = RateLimiter(max_calls=50, period=60)
limiter.wait_if_needed()  # Will block if rate limit exceeded
```

### 3. Input Validation

Comprehensive input validation:

```python
from core.error_handler import InputValidator

symbol = InputValidator.validate_symbol('RELIANCE')
quantity = InputValidator.validate_quantity(10)
price = InputValidator.validate_price(2500.0)
```

### 4. Market Data Utilities

Technical indicators and analysis:

```python
from core.market_data import MarketDataUtils

# Calculate indicators
sma = MarketDataUtils.calculate_sma(prices, period=20)
rsi = MarketDataUtils.calculate_rsi(prices, period=14)
macd = MarketDataUtils.calculate_macd(prices)
bollinger = MarketDataUtils.calculate_bollinger_bands(prices)
```

## Troubleshooting

### Issue: "Module not found: core"

**Solution:** Make sure you're running from the pyPortMan directory or add it to PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/pyPortMan"
```

### Issue: "Encryption key not found"

**Solution:** Generate and add an encryption key to `.env`:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Issue: "Credentials not found"

**Solution:** Make sure your `.env` file has the correct format:
```bash
ZERODHA_MAIN_USER_ID=your_id
ZERODHA_MAIN_PASSWORD=your_password
```

## Rollback Plan

If you need to rollback to the old version:

1. Keep `pyportmanlib.py` as your main import
2. Continue using `auth_info.xlsx` for credentials
3. Revert any code changes

The old `pyportmanlib.py` is still fully functional.

## Support

For issues or questions:
- Check the logs in `logs/` directory
- Enable DEBUG logging in `.env`: `PYPORTMAN_LOG_LEVEL=DEBUG`
- Review error messages for detailed information
