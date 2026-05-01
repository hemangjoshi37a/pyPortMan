# pyPortMan API Documentation

## Overview

pyPortMan provides a comprehensive Python API for managing multiple broker accounts, placing orders, tracking portfolios, and fetching market data.

## Installation

```bash
pip install pyportman
```

## Quick Start

```python
from pyportman import ClientManager, OrderManager, PortfolioManager, MarketDataManager
from pyportman import get_config, get_config_manager

# Load configuration
config = get_config()

# Create client manager
client_manager = ClientManager()

# Add and authenticate a Zerodha account
client = client_manager.add_client(
    broker='zerodha',
    account_name='main',
    credentials={
        'user_id': 'YOUR_USER_ID',
        'password': 'YOUR_PASSWORD',
        'totp_key': 'YOUR_TOTP_SECRET',
        'totp_enabled': True
    }
)

# Login
client.login()

# Create managers
order_manager = OrderManager(client)
portfolio_manager = PortfolioManager(client)
market_manager = MarketDataManager(client)

# Get portfolio summary
summary = portfolio_manager.get_portfolio_summary()
print(f"Total P&L: {summary.total_pnl}")

# Get holdings
holdings = portfolio_manager.get_holdings()
for holding in holdings:
    print(f"{holding.symbol}: {holding.pnl}")

# Place an order
order = order_manager.place_order(
    symbol='RELIANCE',
    quantity=10,
    transaction_type='BUY',
    order_type='MARKET',
    product='CNC'
)
print(f"Order placed: {order.order_id}")

# Get market quote
quote = market_manager.get_quote('RELIANCE')
print(f"RELIANCE LTP: {quote.last_price}")
```

## Configuration

### Environment Variables

```bash
# Encryption key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
PYPORTMAN_ENCRYPTION_KEY=your-encryption-key-here

# Environment
PYPORTMAN_ENV=development

# Configuration directory
PYPORTMAN_CONFIG_DIR=/path/to/config
```

### Configuration File

Configuration files are stored in JSON format with environment-specific settings:

```json
{
  "environment": "development",
  "debug": true,
  "zerodha": {
    "enabled": true,
    "rate_limit": 50,
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "enable_cache": true,
    "cache_duration": 300
  },
  "angel": {
    "enabled": true,
    "rate_limit": 50,
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "enable_cache": true,
    "cache_duration": 300
  },
  "logging": {
    "level": "INFO",
    "log_to_file": true,
    "log_dir": "logs"
  },
  "security": {
    "enable_totp": true,
    "session_timeout": 3600,
    "max_login_attempts": 3
  },
  "alerts": {
    "telegram_enabled": false,
    "discord_enabled": false,
    "email_enabled": false
  }
}
```

### Programmatic Configuration

```python
from pyportman import ConfigManager, PyPortManConfig, BrokerConfig

# Create config manager
config_manager = ConfigManager()

# Get current config
config = config_manager.get_config()

# Update broker config
config_manager.update_broker_config('zerodha', rate_limit=100)

# Save config
config_manager.save_config(config)
```

## Client Management

### ClientManager

Manages multiple broker client instances.

```python
from pyportman import ClientManager

client_manager = ClientManager()

# Add a client
client = client_manager.add_client(
    broker='zerodha',
    account_name='main',
    credentials={
        'user_id': 'YOUR_USER_ID',
        'password': 'YOUR_PASSWORD',
        'totp_key': 'YOUR_TOTP_SECRET',
        'totp_enabled': True
    }
)

# Get existing client
client = client_manager.get_client('zerodha', 'main')

# Remove client
client_manager.remove_client('zerodha', 'main')

# Login all clients
results = client_manager.login_all()

# Get all clients
clients = client_manager.get_all_clients()

# Get authenticated clients
auth_clients = client_manager.get_authenticated_clients()
```

### BrokerClient

Base class for broker-specific clients.

```python
# Check authentication status
if client.is_authenticated():
    print("Client is authenticated")

# Get profile
profile = client.get_profile()
print(f"User: {profile['user_name']}")

# Check funds
funds = client.check_funds()
print(f"Equity: {funds['equity']}")
print(f"Commodity: {funds['commodity']}")

# Refresh session
client.refresh_session()

# Logout
client.logout()
```

## Order Management

### OrderManager

Manages order placement, modification, and cancellation.

```python
from pyportman import OrderManager

order_manager = OrderManager(client)

# Place a market order
order = order_manager.place_order(
    symbol='RELIANCE',
    quantity=10,
    transaction_type='BUY',
    order_type='MARKET',
    product='CNC'
)

# Place a limit order
order = order_manager.place_order(
    symbol='RELIANCE',
    quantity=10,
    transaction_type='BUY',
    order_type='LIMIT',
    price=2500.0,
    product='CNC'
)

# Place a stop-loss order
order = order_manager.place_order(
    symbol='RELIANCE',
    quantity=10,
    transaction_type='SELL',
    order_type='SL',
    price=2600.0,
    trigger_price=2550.0,
    product='CNC'
)

# Place a bracket order
order = order_manager.place_order(
    symbol='RELIANCE',
    quantity=10,
    transaction_type='BUY',
    order_type='LIMIT',
    price=2500.0,
    product='BO',
    squareoff=100.0,
    stoploss=50.0
)

# Cancel an order
success = order_manager.cancel_order(order.order_id)

# Modify an order
success = order_manager.modify_order(
    order_id=order.order_id,
    price=2510.0,
    quantity=15
)

# Get all orders
orders = order_manager.get_orders()

# Get pending orders
pending_orders = order_manager.get_pending_orders()
```

### GTT Orders (Zerodha Only)

```python
# Place a GTT order
gtt_order = order_manager.place_gtt_order(
    symbol='RELIANCE',
    trigger_price=2400.0,
    target_price=2600.0,
    quantity=10,
    transaction_type='BUY',
    stop_loss=2350.0
)

# Cancel a GTT order
success = order_manager.cancel_gtt_order(gtt_order.gtt_id)

# Get all GTT orders
gtt_orders = order_manager.get_gtt_orders()
```

### Order Types

- `MARKET`: Market order
- `LIMIT`: Limit order
- `SL`: Stop-loss order
- `SL-M`: Stop-loss market order

### Transaction Types

- `BUY`: Buy order
- `SELL`: Sell order

### Product Types

- `CNC`: Cash and Carry (delivery)
- `MIS`: Margin Intraday Squareoff
- `NRML`: Normal (F&O)
- `BO`: Bracket Order
- `CO`: Cover Order

### Order Validity

- `DAY`: Valid for the day
- `IOC`: Immediate or Cancel
- `GTD`: Good Till Date

## Portfolio Management

### PortfolioManager

Manages portfolio data including holdings, positions, and P&L.

```python
from pyportman import PortfolioManager

portfolio_manager = PortfolioManager(client)

# Get holdings
holdings = portfolio_manager.get_holdings()
for holding in holdings:
    print(f"{holding.symbol}: {holding.quantity} @ {holding.average_price}")
    print(f"  LTP: {holding.ltp}, P&L: {holding.pnl}")

# Get positions
positions = portfolio_manager.get_positions()
for position in positions:
    print(f"{position.symbol}: {position.quantity}")
    print(f"  P&L: {position.pnl}")

# Get portfolio summary
summary = portfolio_manager.get_portfolio_summary()
print(f"Total Value: {summary.total_value}")
print(f"Total P&L: {summary.total_pnl}")
print(f"Holdings: {summary.holdings_count}")
print(f"Positions: {summary.positions_count}")

# Calculate P&L
pnl = portfolio_manager.calculate_pnl()
print(f"Holdings P&L: {pnl['holdings_pnl']}")
print(f"Positions P&L: {pnl['positions_pnl']}")

# Get sector allocation
sectors = portfolio_manager.get_sector_allocation()
for sector, data in sectors.items():
    print(f"{sector}: {data['count']} stocks, {data['value']} value")

# Get top performers
performers = portfolio_manager.get_top_performers(n=5)
print("Top Gainers:")
for gainer in performers['top_gainers']:
    print(f"  {gainer['symbol']}: {gainer['pnl']}")

# Refresh cached data
portfolio_manager.refresh()
```

### Multi-Account Portfolio

```python
from pyportman import MultiAccountPortfolioManager

# Create multi-account manager
multi_manager = MultiAccountPortfolioManager(clients)

# Get consolidated holdings
consolidated = multi_manager.get_consolidated_holdings()
print(f"Total holdings: {consolidated['summary']['total_count']}")
print(f"Total value: {consolidated['summary']['total_value']}")

# Get consolidated positions
positions = multi_manager.get_consolidated_positions()

# Get consolidated summary
summary = multi_manager.get_consolidated_summary()

# Get total funds
funds = multi_manager.get_total_funds()
print(f"Total equity: {funds['total_equity']}")
print(f"Total commodity: {funds['total_commodity']}")
```

## Market Data

### MarketDataManager

Fetches market data including quotes and historical data.

```python
from pyportman import MarketDataManager

market_manager = MarketDataManager(client)

# Get quote for a symbol
quote = market_manager.get_quote('RELIANCE')
print(f"LTP: {quote.last_price}")
print(f"Change: {quote.change} ({quote.change_percent}%)")
print(f"Volume: {quote.volume}")
print(f"High: {quote.high}, Low: {quote.low}")

# Get quotes for multiple symbols
quotes = market_manager.get_quotes(['RELIANCE', 'TCS', 'INFY'])
for symbol, quote in quotes.items():
    print(f"{symbol}: {quote.last_price}")

# Get historical data
import pandas as pd
df = market_manager.get_historical_data(
    symbol='RELIANCE',
    from_date='2024-01-01',
    to_date='2024-01-31',
    interval='day'
)
print(df.head())

# Get intraday data
intraday = market_manager.get_intraday_data(
    symbol='RELIANCE',
    interval='5minute',
    days=1
)
print(intraday.head())
```

### Market Data Utilities

```python
from pyportman import MarketDataUtils

# Calculate returns
returns = MarketDataUtils.calculate_returns(df['close'])

# Calculate volatility
volatility = MarketDataUtils.calculate_volatility(df['close'], window=20)

# Calculate RSI
rsi = MarketDataUtils.calculate_rsi(df['close'], period=14)

# Calculate SMA
sma = MarketDataUtils.calculate_sma(df['close'], period=20)

# Calculate EMA
ema = MarketDataUtils.calculate_ema(df['close'], period=20)

# Calculate Bollinger Bands
bb = MarketDataUtils.calculate_bollinger_bands(df['close'], period=20, std_dev=2.0)
print(f"Upper: {bb['upper'].iloc[-1]}")
print(f"Middle: {bb['middle'].iloc[-1]}")
print(f"Lower: {bb['lower'].iloc[-1]}")

# Calculate MACD
macd = MarketDataUtils.calculate_macd(df['close'])
print(f"MACD: {macd['macd'].iloc[-1]}")
print(f"Signal: {macd['signal'].iloc[-1]}")

# Detect support and resistance
levels = MarketDataUtils.detect_support_resistance(df['close'], window=20)
print(f"Support: {levels['support']}")
print(f"Resistance: {levels['resistance']}")

# Calculate ATR
atr = MarketDataUtils.calculate_atr(df['high'], df['low'], df['close'])
```

## Async Support

### Async HTTP Client

For concurrent API calls:

```python
import asyncio
from pyportman import AsyncHTTPClient, AsyncRequest

async def fetch_multiple_quotes():
    async with AsyncHTTPClient(max_concurrent=10) as client:
        # Create requests
        requests = [
            AsyncRequest(url=f"https://api.example.com/quote/{symbol}")
            for symbol in ['RELIANCE', 'TCS', 'INFY']
        ]

        # Fetch concurrently
        responses = await client.batch_request(requests)

        for response in responses:
            if response.success:
                print(f"Status: {response.status_code}, Data: {response.data}")

asyncio.run(fetch_multiple_quotes())
```

### Async Batch Processor

```python
from pyportman import AsyncBatchProcessor

async def process_items():
    processor = AsyncBatchProcessor(max_concurrent=5)

    items = [1, 2, 3, 4, 5]

    async def process_item(item):
        # Your async processing logic
        await asyncio.sleep(0.1)
        return item * 2

    results = await processor.process(items, process_item)
    print(results)

asyncio.run(process_items())
```

## Error Handling

### Custom Exceptions

```python
from pyportman import (
    PyPortManError,
    AuthenticationError,
    OrderError,
    MarketDataError,
    PortfolioError,
    RateLimitError,
    ValidationError
)

try:
    order = order_manager.place_order(...)
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except OrderError as e:
    print(f"Order failed: {e.message}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e.message}")
    print(f"Retry after: {e.retry_after} seconds")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
except PyPortManError as e:
    print(f"Error: {e.message}")
```

### Retry Decorator

```python
from pyportman import retry_on_failure

@retry_on_failure(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
def place_order_with_retry():
    # This will retry up to 3 times with exponential backoff
    return order_manager.place_order(...)
```

### Error Handling Decorator

```python
from pyportman import with_error_handling

@with_error_handling(logger=logger, raise_on_error=False, default_return=None)
def safe_operation():
    # This will catch errors and return None instead of raising
    return risky_operation()
```

## Security

### Credential Management

```python
from pyportman import CredentialManager

# Create credential manager
cred_manager = CredentialManager()

# Get broker credentials
credentials = cred_manager.get_broker_credentials('zerodha', 'main')

# Encrypt sensitive data
encrypted = cred_manager.encrypt('my_secret_password')

# Decrypt sensitive data
decrypted = cred_manager.decrypt(encrypted)

# Validate credentials
try:
    cred_manager.validate_credentials(credentials)
except ValidationError as e:
    print(f"Invalid credentials: {e.message}")
```

### Password Hashing

```python
from pyportman import PasswordHasher

# Hash password
hashed, salt = PasswordHasher.hash_password('my_password')

# Verify password
is_valid = PasswordHasher.verify_password('my_password', hashed, salt)
```

### Data Masking

```python
from pyportman import mask_sensitive_data, sanitize_log_data

# Mask sensitive data
masked = mask_sensitive_data('my_api_key_12345')
print(masked)  # Output: my_a****_12345

# Sanitize log data
data = {
    'user_id': 'john',
    'password': 'secret123',
    'api_key': 'abc123xyz'
}
sanitized = sanitize_log_data(data)
print(sanitized)
# Output: {'user_id': 'john', 'password': '****', 'api_key': '****'}
```

## Logging

### Logger Configuration

```python
from pyportman import get_logger, PyPortManLogger

# Get a logger
logger = get_logger('my_module')

# Log messages
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")

# Set log level
PyPortManLogger.set_log_level(logging.DEBUG)
```

## Testing

### Unit Tests

```python
import pytest
from pyportman import OrderManager, ValidationError

def test_order_validation():
    order_manager = OrderManager(client)

    # Test invalid quantity
    with pytest.raises(ValidationError):
        order_manager.place_order(
            symbol='RELIANCE',
            quantity=-1,  # Invalid
            transaction_type='BUY',
            order_type='MARKET'
        )

    # Test invalid symbol
    with pytest.raises(ValidationError):
        order_manager.place_order(
            symbol='',  # Invalid
            quantity=10,
            transaction_type='BUY',
            order_type='MARKET'
        )
```

### Integration Tests

```python
import pytest
from pyportman import ClientManager

@pytest.mark.integration
def test_zerodha_login():
    client_manager = ClientManager()

    client = client_manager.add_client(
        broker='zerodha',
        account_name='test',
        credentials={
            'user_id': 'TEST_USER',
            'password': 'TEST_PASS',
            'totp_key': 'TEST_TOTP',
            'totp_enabled': True
        }
    )

    result = client.login()
    assert result is True
    assert client.is_authenticated()
```

## Best Practices

1. **Always validate input** before making API calls
2. **Use retry logic** for network operations
3. **Handle errors gracefully** with try-except blocks
4. **Use rate limiting** to avoid API rate limits
5. **Cache data** when appropriate to reduce API calls
6. **Use async operations** for concurrent requests
7. **Keep credentials secure** using encryption
8. **Log important events** for debugging
9. **Test thoroughly** before production use
10. **Monitor rate limits** to avoid being blocked

## Troubleshooting

### Common Issues

**Authentication Failed**
- Check credentials are correct
- Verify TOTP is working
- Check account is active

**Rate Limit Exceeded**
- Reduce request frequency
- Use batch requests
- Implement caching

**Order Placement Failed**
- Check account balance
- Verify order parameters
- Check market hours

**Network Errors**
- Check internet connection
- Verify API endpoints
- Increase timeout values

## Support

For issues and questions:
- GitHub: https://github.com/hemangjoshi37a/pyPortMan
- Email: hemangjoshi37a@gmail.com
- Documentation: https://pyportman.readthedocs.io

## License

MIT License - see LICENSE file for details
