"""Sample order data for testing"""

from datetime import datetime
from core.orders import OrderType, TransactionType, ProductType, OrderStatus, OrderValidity

SAMPLE_ORDERS = [
    {
        'order_id': 'ORD123456',
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'transaction_type': TransactionType.BUY,
        'order_type': OrderType.LIMIT,
        'quantity': 10,
        'price': 2500.0,
        'trigger_price': None,
        'product': ProductType.CNC,
        'status': OrderStatus.COMPLETE,
        'average_price': 2498.5,
        'filled_quantity': 10,
        'pending_quantity': 0,
        'timestamp': datetime.now(),
        'validity': OrderValidity.DAY,
        'variety': 'REGULAR'
    },
    {
        'order_id': 'ORD123457',
        'symbol': 'TCS',
        'exchange': 'NSE',
        'transaction_type': TransactionType.BUY,
        'order_type': OrderType.LIMIT,
        'quantity': 5,
        'price': 3500.0,
        'trigger_price': None,
        'product': ProductType.CNC,
        'status': OrderStatus.PENDING,
        'average_price': 0.0,
        'filled_quantity': 0,
        'pending_quantity': 5,
        'timestamp': datetime.now(),
        'validity': OrderValidity.DAY,
        'variety': 'REGULAR'
    },
    {
        'order_id': 'ORD123458',
        'symbol': 'INFY',
        'exchange': 'NSE',
        'transaction_type': TransactionType.SELL,
        'order_type': OrderType.MARKET,
        'quantity': 20,
        'price': 0.0,
        'trigger_price': None,
        'product': ProductType.MIS,
        'status': OrderStatus.COMPLETE,
        'average_price': 1450.0,
        'filled_quantity': 20,
        'pending_quantity': 0,
        'timestamp': datetime.now(),
        'validity': OrderValidity.IOC,
        'variety': 'REGULAR'
    },
    {
        'order_id': 'ORD123459',
        'symbol': 'HDFC',
        'exchange': 'NSE',
        'transaction_type': TransactionType.BUY,
        'order_type': OrderType.STOP_LOSS,
        'quantity': 15,
        'price': 1600.0,
        'trigger_price': 1590.0,
        'product': ProductType.NRML,
        'status': OrderStatus.TRIGGER_PENDING,
        'average_price': 0.0,
        'filled_quantity': 0,
        'pending_quantity': 15,
        'timestamp': datetime.now(),
        'validity': OrderValidity.DAY,
        'variety': 'REGULAR'
    },
    {
        'order_id': 'ORD123460',
        'symbol': 'ICICI',
        'exchange': 'NSE',
        'transaction_type': TransactionType.SELL,
        'order_type': OrderType.LIMIT,
        'quantity': 30,
        'price': 950.0,
        'trigger_price': None,
        'product': ProductType.CNC,
        'status': OrderStatus.CANCELLED,
        'average_price': 0.0,
        'filled_quantity': 0,
        'pending_quantity': 30,
        'timestamp': datetime.now(),
        'validity': OrderValidity.DAY,
        'variety': 'REGULAR'
    }
]

SAMPLE_GTT_ORDERS = [
    {
        'gtt_id': 'GTT123456',
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'trigger_price': 2550.0,
        'target_price': 2600.0,
        'quantity': 10,
        'transaction_type': TransactionType.BUY,
        'stop_loss': 2450.0,
        'status': 'ACTIVE',
        'created_at': datetime.now(),
        'triggered_at': None
    },
    {
        'gtt_id': 'GTT123457',
        'symbol': 'TCS',
        'exchange': 'NSE',
        'trigger_price': 3550.0,
        'target_price': 3600.0,
        'quantity': 5,
        'transaction_type': TransactionType.SELL,
        'stop_loss': 3450.0,
        'status': 'TRIGGERED',
        'created_at': datetime.now(),
        'triggered_at': datetime.now()
    },
    {
        'gtt_id': 'GTT123458',
        'symbol': 'INFY',
        'exchange': 'NSE',
        'trigger_price': 1500.0,
        'target_price': 1550.0,
        'quantity': 20,
        'transaction_type': TransactionType.BUY,
        'stop_loss': 1450.0,
        'status': 'CANCELLED',
        'created_at': datetime.now(),
        'triggered_at': None
    }
]
