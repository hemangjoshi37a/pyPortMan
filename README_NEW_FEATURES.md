# New Features Implementation

This document describes the new features added to pyPortMan.

## Features Implemented

### 1. Multi-Broker Support (`multi_broker_support.py`)

Support for 5Paisa, Upstox, and Dhan brokers with unified portfolio view.

#### Supported Brokers
- **5Paisa** - Full API integration
- **Upstox** - OAuth-based authentication
- **Dhan** - REST API support

#### Key Features
- Unified portfolio view across all brokers
- Broker arbitrage opportunities detection
- Cross-broker order placement
- Consolidated holdings, positions, and orders

#### Usage Example
```python
from multi_broker_support import UnifiedPortfolioManager, create_broker

# Create portfolio manager
manager = UnifiedPortfolioManager()

# Add brokers
broker1 = create_broker("5paisa", api_key="xxx", api_secret="xxx",
                       user_id="xxx", password="xxx", client_id="xxx")
broker2 = create_broker("upstox", api_key="xxx", api_secret="xxx",
                       user_id="xxx", password="xxx")

manager.add_broker("5paisa", broker1)
manager.add_broker("upstox", broker2)

# Login to all brokers
manager.login_all()

# Get unified holdings
holdings = manager.get_unified_holdings()

# Find arbitrage opportunities
arbitrage = manager.find_arbitrage_opportunities(["RELIANCE", "TCS"])

# Export portfolio
filename = manager.export_portfolio(format="excel")
```

---

### 2. Market Data Integration (`market_data_integration.py`)

NSE/BSE live data feeds, option chain, F&O data, and corporate actions tracking.

#### Data Providers
- **NSE** - Official NSE API
- **BSE** - BSE API integration

#### Key Features
- Real-time quotes
- Historical data (OHLCV)
- Option chain with Greeks
- F&O data
- Corporate actions
- Market movers (gainers/losers)
- Index data
- Put-Call Ratio (PCR)
- Max Pain calculation

#### Usage Example
```python
from market_data_integration import MarketDataManager

# Create data manager
manager = MarketDataManager()

# Get quote
quote = manager.get_quote("RELIANCE", exchange="NSE")

# Get historical data
historical = manager.get_historical_data("RELIANCE", interval="day",
                                        from_date="01-01-2024",
                                        to_date="31-12-2024")

# Get option chain
options = manager.get_option_chain("NIFTY", expiry="2024-12-26")

# Get F&O data
fo_data = manager.get_fo_data("RELIANCE")

# Get corporate actions
actions = manager.get_corporate_actions("RELIANCE")

# Get market movers
movers = manager.get_market_movers(top_n=10)
```

---

### 3. Advanced Charting (`advanced_charting.py`)

Candlestick charts with technical indicators and multi-stock comparison.

#### Technical Indicators
- **Moving Averages**: SMA, EMA
- **Momentum**: RSI, Stochastic, Williams %R
- **Trend**: MACD, ADX, Supertrend
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, VWAP
- **Custom**: Ichimoku Cloud, Heikin Ashi

#### Key Features
- Candlestick charts
- Multiple indicators overlay
- Multi-stock comparison
- Correlation heatmap
- Performance summary
- Custom indicator builder

#### Usage Example
```python
from advanced_charting import CandlestickChart, MultiStockComparison

# Create candlestick chart
chart = CandlestickChart(figsize=(14, 10))
fig = chart.create_chart(data, indicators=['sma_20', 'sma_50', 'rsi', 'macd', 'bollinger'])
chart.save_chart("chart.png")

# Multi-stock comparison
comparison = MultiStockComparison()
fig = comparison.compare_stocks({
    "RELIANCE": reliance_data,
    "TCS": tcs_data,
    "INFY": infy_data
})

# Correlation heatmap
heatmap = comparison.correlation_heatmap(stocks_data)

# Performance summary
summary = comparison.performance_summary(stocks_data)
```

---

### 4. Tax Reporting (`tax_reporting.py`)

Capital gains calculation (STCG/LTCG), tax-ready reports, and financial year summaries.

#### Tax Features
- FIFO-based capital gains calculation
- STCG/LTCG classification
- Indexation benefit for non-equity assets
- Asset-wise breakdown
- Symbol-wise breakdown
- ITR form data generation
- Excel/JSON export

#### Tax Rates (FY 2024-25)
- **Equity STCG**: 15% (held < 1 year)
- **Equity LTCG**: 10% on gains above ₹1 lakh (held ≥ 1 year)
- **Other STCG**: As per income slab
- **Other LTCG**: 20% with indexation

#### Usage Example
```python
from tax_reporting import TaxCalculator, TaxReportGenerator, TaxYear

# Create tax calculator
calculator = TaxCalculator()

# Add transactions
calculator.add_transactions_from_dataframe(tradebook_df)

# Calculate capital gains
gains = calculator.calculate_capital_gains(TaxYear.FY_2024_25)

# Get tax summary
summary = calculator.get_tax_summary(TaxYear.FY_2024_25)

# Generate reports
report_gen = TaxReportGenerator(calculator)

# Export to Excel
filename = report_gen.export_to_excel(TaxYear.FY_2024_25)

# Generate ITR form data
itr_data = report_gen.generate_itr_form_data(TaxYear.FY_2024_25)
```

---

## Installation

Install the required dependencies:

```bash
pip install pandas numpy matplotlib requests scipy openpyxl
```

For Jupyter notebook usage:

```bash
pip install jupyter notebook ipywidgets qgrid
```

---

## File Structure

```
pyPortMan/
├── multi_broker_support.py      # Multi-broker integration
├── market_data_integration.py   # Market data providers
├── advanced_charting.py         # Charting and indicators
├── tax_reporting.py             # Tax calculation and reports
├── hjOpenTerminal.ipynb         # Main notebook
├── auth_info.xlsx               # Broker credentials
├── stocks.xlsx                  # Stock list
└── README_NEW_FEATURES.md       # This file
```

---

## API Reference

### Multi-Broker Support

#### Classes
- `BrokerBase` - Base broker class
- `FivePaisaBroker` - 5Paisa integration
- `UpstoxBroker` - Upstox integration
- `DhanBroker` - Dhan integration
- `UnifiedPortfolioManager` - Portfolio manager

#### Methods
- `login()` - Authenticate with broker
- `get_holdings()` - Get holdings
- `get_positions()` - Get positions
- `get_orders()` - Get orders
- `place_order()` - Place order
- `cancel_order()` - Cancel order
- `get_quote()` - Get quote

### Market Data Integration

#### Classes
- `MarketDataProvider` - Base provider class
- `NSEDataProvider` - NSE data provider
- `BSEDataProvider` - BSE data provider
- `MarketDataManager` - Unified data manager

#### Methods
- `get_quote()` - Get live quote
- `get_historical_data()` - Get historical data
- `get_option_chain()` - Get option chain
- `get_fo_data()` - Get F&O data
- `get_corporate_actions()` - Get corporate actions
- `get_market_movers()` - Get gainers/losers

### Advanced Charting

#### Classes
- `TechnicalIndicators` - Indicator calculations
- `CandlestickChart` - Chart creation
- `MultiStockComparison` - Multi-stock analysis
- `CustomIndicator` - Custom indicator builder

#### Indicators
- `sma()` - Simple Moving Average
- `ema()` - Exponential Moving Average
- `rsi()` - Relative Strength Index
- `macd()` - MACD
- `bollinger_bands()` - Bollinger Bands
- `stochastic()` - Stochastic Oscillator
- `atr()` - Average True Range
- `adx()` - Average Directional Index

### Tax Reporting

#### Classes
- `TaxCalculator` - Tax calculation engine
- `TaxReportGenerator` - Report generator
- `TaxYear` - Financial year enum
- `TransactionType` - Transaction type enum
- `AssetType` - Asset type enum

#### Methods
- `calculate_capital_gains()` - Calculate gains
- `get_tax_summary()` - Get summary
- `export_to_excel()` - Export to Excel
- `export_to_json()` - Export to JSON
- `generate_itr_form_data()` - Generate ITR data

---

## Examples

### Example 1: Complete Workflow

```python
from multi_broker_support import UnifiedPortfolioManager, create_broker
from market_data_integration import MarketDataManager
from advanced_charting import CandlestickChart
from tax_reporting import TaxCalculator, TaxReportGenerator, TaxYear

# 1. Setup multi-broker portfolio
manager = UnifiedPortfolioManager()
broker = create_broker("zerodha", api_key="xxx", api_secret="xxx",
                       user_id="xxx", password="xxx")
manager.add_broker("zerodha", broker)
manager.login_all()

# 2. Get market data
data_manager = MarketDataManager()
quote = data_manager.get_quote("RELIANCE")
historical = data_manager.get_historical_data("RELIANCE")

# 3. Create chart
chart = CandlestickChart()
fig = chart.create_chart(historical, indicators=['sma_20', 'rsi', 'macd'])
chart.save_chart("reliance_chart.png")

# 4. Generate tax report
calculator = TaxCalculator()
calculator.add_transactions_from_dataframe(tradebook)
report_gen = TaxReportGenerator(calculator)
report_gen.export_to_excel(TaxYear.FY_2024_25)
```

### Example 2: Arbitrage Detection

```python
from multi_broker_support import UnifiedPortfolioManager, create_broker

manager = UnifiedPortfolioManager()

# Add multiple brokers
for broker_name in ["zerodha", "5paisa", "upstox"]:
    broker = create_broker(broker_name, **broker_config[broker_name])
    manager.add_broker(broker_name, broker)

manager.login_all()

# Find arbitrage opportunities
symbols = ["RELIANCE", "TCS", "INFY", "HDFC"]
arbitrage = manager.find_arbitrage_opportunities(symbols)

print(arbitrage)
```

### Example 3: Option Chain Analysis

```python
from market_data_integration import MarketDataManager

manager = MarketDataManager()

# Get option chain
options = manager.get_option_chain("NIFTY", expiry="2024-12-26")

# Calculate PCR
from market_data_integration import calculate_pcr
pcr = calculate_pcr(options)

# Calculate Max Pain
from market_data_integration import calculate_max_pain
max_pain = calculate_max_pain(options)

print(f"PCR: {pcr:.2f}")
print(f"Max Pain: {max_pain}")
```

---

## Notes

- All broker APIs require valid credentials
- Market data may have rate limits
- Tax calculations are based on Indian tax laws for FY 2024-25
- Charts require matplotlib backend for display

---

## Support

For issues or questions, please refer to the main README or contact the project maintainers.
