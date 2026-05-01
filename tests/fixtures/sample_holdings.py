"""Sample holdings data for testing"""

from datetime import datetime

SAMPLE_HOLDINGS = [
    {
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'quantity': 50,
        'average_price': 2400.0,
        'ltp': 2500.0,
        'pnl': 5000.0,
        'day_change': 50.0,
        'day_change_percent': 2.08,
        'product': 'CNC'
    },
    {
        'symbol': 'TCS',
        'exchange': 'NSE',
        'quantity': 20,
        'average_price': 3400.0,
        'ltp': 3500.0,
        'pnl': 2000.0,
        'day_change': 30.0,
        'day_change_percent': 0.88,
        'product': 'CNC'
    },
    {
        'symbol': 'INFY',
        'exchange': 'NSE',
        'quantity': 100,
        'average_price': 1400.0,
        'ltp': 1450.0,
        'pnl': 5000.0,
        'day_change': 20.0,
        'day_change_percent': 1.40,
        'product': 'CNC'
    },
    {
        'symbol': 'HDFC',
        'exchange': 'NSE',
        'quantity': 30,
        'average_price': 1550.0,
        'ltp': 1600.0,
        'pnl': 1500.0,
        'day_change': 25.0,
        'day_change_percent': 1.59,
        'product': 'CNC'
    },
    {
        'symbol': 'ICICI',
        'exchange': 'NSE',
        'quantity': 80,
        'average_price': 900.0,
        'ltp': 950.0,
        'pnl': 4000.0,
        'day_change': 15.0,
        'day_change_percent': 1.61,
        'product': 'CNC'
    },
    {
        'symbol': 'SBIN',
        'exchange': 'NSE',
        'quantity': 200,
        'average_price': 550.0,
        'ltp': 580.0,
        'pnl': 6000.0,
        'day_change': 10.0,
        'day_change_percent': 1.75,
        'product': 'CNC'
    },
    {
        'symbol': 'AXISBANK',
        'exchange': 'NSE',
        'quantity': 60,
        'average_price': 1000.0,
        'ltp': 980.0,
        'pnl': -1200.0,
        'day_change': -5.0,
        'day_change_percent': -0.51,
        'product': 'CNC'
    },
    {
        'symbol': 'WIPRO',
        'exchange': 'NSE',
        'quantity': 40,
        'average_price': 450.0,
        'ltp': 470.0,
        'pnl': 800.0,
        'day_change': 8.0,
        'day_change_percent': 1.74,
        'product': 'CNC'
    },
    {
        'symbol': 'HCLTECH',
        'exchange': 'NSE',
        'quantity': 25,
        'average_price': 1200.0,
        'ltp': 1250.0,
        'pnl': 1250.0,
        'day_change': 18.0,
        'day_change_percent': 1.46,
        'product': 'CNC'
    },
    {
        'symbol': 'TATAMOTORS',
        'exchange': 'NSE',
        'quantity': 150,
        'average_price': 600.0,
        'ltp': 650.0,
        'pnl': 7500.0,
        'day_change': 12.0,
        'day_change_percent': 1.88,
        'product': 'CNC'
    }
]

SAMPLE_POSITIONS = [
    {
        'symbol': 'NIFTY',
        'exchange': 'NFO',
        'quantity': 50,
        'buy_price': 24500.0,
        'sell_price': None,
        'ltp': 24550.0,
        'pnl': 2500.0,
        'product': 'MIS',
        'position_type': 'LONG'
    },
    {
        'symbol': 'BANKNIFTY',
        'exchange': 'NFO',
        'quantity': 25,
        'buy_price': 47800.0,
        'sell_price': None,
        'ltp': 47750.0,
        'pnl': -1250.0,
        'product': 'MIS',
        'position_type': 'LONG'
    },
    {
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'quantity': 10,
        'buy_price': 2480.0,
        'sell_price': None,
        'ltp': 2500.0,
        'pnl': 200.0,
        'product': 'MIS',
        'position_type': 'LONG'
    },
    {
        'symbol': 'TCS',
        'exchange': 'NSE',
        'quantity': 5,
        'buy_price': 3520.0,
        'sell_price': None,
        'ltp': 3500.0,
        'pnl': -100.0,
        'product': 'MIS',
        'position_type': 'LONG'
    },
    {
        'symbol': 'INFY',
        'exchange': 'NSE',
        'quantity': 20,
        'buy_price': 1430.0,
        'sell_price': None,
        'ltp': 1450.0,
        'pnl': 400.0,
        'product': 'MIS',
        'position_type': 'LONG'
    }
]

SAMPLE_PORTFOLIO_SUMMARY = {
    'account_name': 'test_account',
    'broker': 'zerodha',
    'funds_equity': 100000.0,
    'funds_commodity': 50000.0,
    'total_funds': 150000.0,
    'holdings_count': 10,
    'holdings_value': 250000.0,
    'holdings_pnl': 29350.0,
    'positions_count': 5,
    'positions_value': 175000.0,
    'positions_pnl': 1750.0,
    'total_pnl': 31100.0,
    'pending_orders': 3,
    'timestamp': datetime.now()
}
