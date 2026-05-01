"""Sample market data for testing"""

from datetime import datetime, timedelta
import pandas as pd

SAMPLE_QUOTES = [
    {
        'symbol': 'RELIANCE',
        'last_price': 2500.0,
        'change': 50.0,
        'change_percent': 2.04,
        'volume': 1000000,
        'open': 2480.0,
        'high': 2520.0,
        'low': 2470.0,
        'close': 2450.0,
        'bid_price': 2499.0,
        'ask_price': 2501.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'TCS',
        'last_price': 3500.0,
        'change': 70.0,
        'change_percent': 2.04,
        'volume': 500000,
        'open': 3480.0,
        'high': 3520.0,
        'low': 3470.0,
        'close': 3450.0,
        'bid_price': 3499.0,
        'ask_price': 3501.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'INFY',
        'last_price': 1450.0,
        'change': 20.0,
        'change_percent': 1.40,
        'volume': 800000,
        'open': 1440.0,
        'high': 1460.0,
        'low': 1435.0,
        'close': 1430.0,
        'bid_price': 1449.0,
        'ask_price': 1451.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'HDFC',
        'last_price': 1600.0,
        'change': 25.0,
        'change_percent': 1.59,
        'volume': 300000,
        'open': 1590.0,
        'high': 1610.0,
        'low': 1585.0,
        'close': 1575.0,
        'bid_price': 1599.0,
        'ask_price': 1601.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'ICICI',
        'last_price': 950.0,
        'change': 15.0,
        'change_percent': 1.61,
        'volume': 1200000,
        'open': 945.0,
        'high': 955.0,
        'low': 940.0,
        'close': 935.0,
        'bid_price': 949.0,
        'ask_price': 951.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'SBIN',
        'last_price': 580.0,
        'change': 10.0,
        'change_percent': 1.75,
        'volume': 2000000,
        'open': 575.0,
        'high': 585.0,
        'low': 570.0,
        'close': 570.0,
        'bid_price': 579.0,
        'ask_price': 581.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'AXISBANK',
        'last_price': 980.0,
        'change': -5.0,
        'change_percent': -0.51,
        'volume': 600000,
        'open': 990.0,
        'high': 995.0,
        'low': 975.0,
        'close': 985.0,
        'bid_price': 979.0,
        'ask_price': 981.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'WIPRO',
        'last_price': 470.0,
        'change': 8.0,
        'change_percent': 1.74,
        'volume': 400000,
        'open': 465.0,
        'high': 475.0,
        'low': 460.0,
        'close': 462.0,
        'bid_price': 469.0,
        'ask_price': 471.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'HCLTECH',
        'last_price': 1250.0,
        'change': 18.0,
        'change_percent': 1.46,
        'volume': 250000,
        'open': 1240.0,
        'high': 1260.0,
        'low': 1235.0,
        'close': 1232.0,
        'bid_price': 1249.0,
        'ask_price': 1251.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    },
    {
        'symbol': 'TATAMOTORS',
        'last_price': 650.0,
        'change': 12.0,
        'change_percent': 1.88,
        'volume': 1500000,
        'open': 645.0,
        'high': 655.0,
        'low': 640.0,
        'close': 638.0,
        'bid_price': 649.0,
        'ask_price': 651.0,
        'timestamp': datetime.now(),
        'exchange': 'NSE'
    }
]

# Generate sample OHLCV data
def generate_sample_ohlcv(symbol='RELIANCE', days=100, start_price=2400.0):
    """Generate sample OHLCV data for testing"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')
    data = []

    price = start_price
    for i, date in enumerate(dates):
        # Random walk
        change = (i % 10 - 5) * 2  # -10 to +10
        price += change

        open_price = price + (i % 5 - 2)
        high = max(open_price, price) + (i % 3)
        low = min(open_price, price) - (i % 3)
        close = price
        volume = 1000000 + (i % 10) * 100000

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'symbol': symbol
        })

    return pd.DataFrame(data)

SAMPLE_OHLCV_DATA = generate_sample_ohlcv()

# Intraday data sample
def generate_sample_intraday(symbol='RELIANCE', intervals=78, start_price=2500.0):
    """Generate sample intraday data (15-minute intervals for 1 day)"""
    dates = pd.date_range(
        start=datetime.now().replace(hour=9, minute=15, second=0),
        periods=intervals,
        freq='15min'
    )
    data = []

    price = start_price
    for i, date in enumerate(dates):
        if date.hour >= 15 and date.minute >= 30:
            break  # Market closes at 3:30 PM

        change = (i % 7 - 3) * 0.5
        price += change

        open_price = price + (i % 3 - 1)
        high = max(open_price, price) + (i % 2)
        low = min(open_price, price) - (i % 2)
        close = price
        volume = 50000 + (i % 5) * 10000

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'symbol': symbol
        })

    return pd.DataFrame(data)

SAMPLE_INTRADAY_DATA = generate_sample_intraday()

# Index data
SAMPLE_INDEX_DATA = {
    'NIFTY50': {
        'last_price': 24500.0,
        'change': 100.0,
        'change_percent': 0.41,
        'high': 24600.0,
        'low': 24400.0,
        'open': 24450.0,
        'close': 24400.0
    },
    'SENSEX': {
        'last_price': 81500.0,
        'change': 350.0,
        'change_percent': 0.43,
        'high': 81700.0,
        'low': 81300.0,
        'open': 81400.0,
        'close': 81150.0
    },
    'BANKNIFTY': {
        'last_price': 47800.0,
        'change': 200.0,
        'change_percent': 0.42,
        'high': 47950.0,
        'low': 47650.0,
        'open': 47750.0,
        'close': 47600.0
    }
}

# Market movers
SAMPLE_MARKET_MOVERS = {
    'gainers': [
        {'symbol': 'RELIANCE', 'change_percent': 2.04, 'price': 2500.0},
        {'symbol': 'TCS', 'change_percent': 2.04, 'price': 3500.0},
        {'symbol': 'INFY', 'change_percent': 1.40, 'price': 1450.0},
        {'symbol': 'HDFC', 'change_percent': 1.59, 'price': 1600.0},
        {'symbol': 'SBIN', 'change_percent': 1.75, 'price': 580.0}
    ],
    'losers': [
        {'symbol': 'AXISBANK', 'change_percent': -0.51, 'price': 980.0},
        {'symbol': 'TATASTEEL', 'change_percent': -0.75, 'price': 120.0},
        {'symbol': 'JSWSTEEL', 'change_percent': -0.65, 'price': 800.0},
        {'symbol': 'MARUTI', 'change_percent': -0.45, 'price': 10200.0},
        {'symbol': 'BAJFINANCE', 'change_percent': -0.35, 'price': 7200.0}
    ]
}
