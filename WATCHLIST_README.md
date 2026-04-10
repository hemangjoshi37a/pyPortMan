# Watchlist Management Feature

## Overview

The Watchlist Management feature allows you to track stocks of interest across your Zerodha accounts. You can organize stocks into categories, set target buy/sell prices, add notes, and get real-time price updates.

## Features

- **Add/Remove Stocks**: Add stocks to your watchlist with custom categories
- **Categories**: Organize stocks into groups (e.g., "Large Cap", "IT", "Banking")
- **Target Prices**: Set desired buy and sell prices for each stock
- **Notes**: Add personal notes about each stock
- **Priority**: Set priority to sort important stocks first
- **Real-time Prices**: Update current prices from Zerodha
- **Search**: Search by stock symbol or notes
- **Bulk Operations**: Add multiple stocks at once
- **Price Targets**: Get alerts when stocks are near your target prices

## API Endpoints

### Get Watchlist
```
GET /watchlist
GET /watchlist/{account_id}
```
Query params:
- `category`: Filter by category
- `include_inactive`: Include inactive items

### Add to Watchlist
```
POST /watchlist
```
Body:
```json
{
  "stock": "RELIANCE",
  "exchange": "NSE",
  "category": "Large Cap",
  "notes": "Good for long term",
  "target_buy_price": 2400.0,
  "target_sell_price": 2800.0,
  "priority": 5
}
```

### Update Watchlist Item
```
PUT /watchlist/{watchlist_id}
```
Body:
```json
{
  "notes": "Updated notes",
  "target_buy_price": 2450.0,
  "priority": 10
}
```

### Remove from Watchlist
```
DELETE /watchlist/{watchlist_id}
```

### Bulk Add
```
POST /watchlist/bulk
```
Body:
```json
{
  "stock_list": [
    {"stock": "TCS", "exchange": "NSE", "category": "IT"},
    {"stock": "INFY", "exchange": "NSE", "category": "IT"}
  ]
}
```

### Update Prices
```
POST /watchlist/update-prices
```
Updates current prices for all watchlist items.

### Get Summary
```
GET /watchlist/summary
```
Returns statistics including total items, gainers/losers count, category breakdown.

### Get Categories
```
GET /watchlist/categories
```
Returns all unique categories.

### Search
```
GET /watchlist/search?search_term=RELIANCE
```

### Get Price Targets
```
GET /watchlist/price-targets
```
Returns stocks within 5% of their target buy/sell prices.

## Database Schema

```sql
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    stock VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) DEFAULT 'NSE',
    category VARCHAR(50) DEFAULT 'Default',
    notes TEXT,
    target_buy_price FLOAT,
    target_sell_price FLOAT,
    current_price FLOAT DEFAULT 0,
    day_change FLOAT DEFAULT 0,
    day_change_pct FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    last_price_update DATETIME,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

## Usage Example

```python
from watchlist_manager import WatchlistManager
from database import get_db

# Get database session
db = next(get_db())
manager = WatchlistManager(db)

# Add a stock to watchlist
item = manager.add_to_watchlist(account_id=1, stock_data={
    "stock": "RELIANCE",
    "exchange": "NSE",
    "category": "Large Cap",
    "notes": "Good for long term",
    "target_buy_price": 2400.0,
    "target_sell_price": 2800.0,
    "priority": 5
})

# Get all watchlist items
watchlist = manager.get_watchlist(account_id=1)

# Update prices
result = manager.update_all_prices(account_id=1)

# Get summary
summary = manager.get_watchlist_summary(account_id=1)

# Search
results = manager.search_watchlist(account_id=1, "RELIANCE")

# Get stocks near target prices
near_targets = manager.get_price_targets(account_id=1)
```

## Testing

Run the test script:
```bash
python test_watchlist.py
```

## Integration with Other Features

- **Price Alerts**: Can be created from watchlist items
- **GTT Orders**: Can place GTT orders for watchlist stocks
- **Analytics**: Watchlist data included in portfolio analytics
- **Telegram Alerts**: Can send alerts when watchlist stocks hit targets
