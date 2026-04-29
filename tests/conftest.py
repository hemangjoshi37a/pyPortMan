"""Pytest fixtures for pyPortMan tests"""

import os
import sys
from datetime import datetime
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import Generator

import pytest
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def clean_env():
    """Clean environment variables before and after test"""
    original_env = os.environ.copy()
    # Remove pyportman env vars
    keys_to_remove = [k for k in os.environ if k.startswith('PYPORTMAN_')]
    for key in keys_to_remove:
        del os.environ[key]
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        'order_id': 'ORD123456',
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'transaction_type': 'BUY',
        'order_type': 'LIMIT',
        'quantity': 10,
        'price': 2500.0,
        'trigger_price': None,
        'product': 'CNC',
        'status': 'COMPLETE',
        'average_price': 2498.5,
        'filled_quantity': 10,
        'pending_quantity': 0,
        'timestamp': datetime.now(),
        'validity': 'DAY',
        'variety': 'REGULAR'
    }


@pytest.fixture
def sample_holding_data():
    """Sample holding data for testing"""
    return {
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'quantity': 50,
        'average_price': 2400.0,
        'ltp': 2500.0,
        'pnl': 5000.0,
        'day_change': 50.0,
        'day_change_percent': 2.08,
        'product': 'CNC'
    }


@pytest.fixture
def sample_position_data():
    """Sample position data for testing"""
    return {
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'quantity': 10,
        'buy_price': 2450.0,
        'sell_price': None,
        'ltp': 2500.0,
        'pnl': 500.0,
        'product': 'MIS',
        'position_type': 'LONG'
    }


@pytest.fixture
def sample_quote_data():
    """Sample quote data for testing"""
    return {
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
    }


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'timestamp': dates,
        'open': [2400 + i * 2 for i in range(100)],
        'high': [2420 + i * 2 for i in range(100)],
        'low': [2380 + i * 2 for i in range(100)],
        'close': [2410 + i * 2 for i in range(100)],
        'volume': [1000000 + i * 10000 for i in range(100)]
    })


@pytest.fixture
def mock_zerodha_client():
    """Mock Zerodha client for testing"""
    client = Mock()
    client.broker = 'zerodha'
    client.account_name = 'test_account'
    client.credentials = {
        'user_id': 'TEST123',
        'password': 'test_pass',
        'api_key': 'test_api_key',
        'totp_key': 'test_totp',
        'totp_enabled': True
    }
    client._authenticated = False
    client._session_data = None

    # Mock API methods
    client.api = Mock()
    client.api.profile.return_value = {'user_id': 'TEST123', 'name': 'Test User'}
    client.api.margins.return_value = {
        'equity': {'available': {'cash': 100000, 'margin_used': 0}},
        'commodity': {'available': {'cash': 50000, 'margin_used': 0}}
    }

    return client


@pytest.fixture
def mock_angel_client():
    """Mock Angel client for testing"""
    client = Mock()
    client.broker = 'angel'
    client.account_name = 'test_account'
    client.credentials = {
        'user_id': 'TEST123',
        'password': 'test_pass',
        'api_key': 'test_api_key',
        'client_id': 'TEST123'
    }
    client._authenticated = False
    client._session_data = None

    # Mock API methods
    client.api = Mock()
    client.api.getProfile.return_value = {'clientcode': 'TEST123', 'name': 'Test User'}
    client.api.rmsLimit.return_value = {
        'net': {'availablecash': 100000}
    }

    return client


@pytest.fixture
def sample_credentials():
    """Sample credentials for testing"""
    return {
        'zerodha': {
            'user_id': 'TEST123',
            'password': 'test_password',
            'api_key': 'test_api_key',
            'totp_key': 'test_totp_key',
            'totp_enabled': True
        },
        'angel': {
            'user_id': 'TEST123',
            'password': 'test_password',
            'api_key': 'test_api_key',
            'client_id': 'TEST123'
        }
    }


@pytest.fixture
def sample_portfolio_summary():
    """Sample portfolio summary for testing"""
    return {
        'account_name': 'test_account',
        'broker': 'zerodha',
        'funds_equity': 100000.0,
        'funds_commodity': 50000.0,
        'total_funds': 150000.0,
        'holdings_count': 5,
        'holdings_value': 75000.0,
        'holdings_pnl': 5000.0,
        'positions_count': 2,
        'positions_value': 25000.0,
        'positions_pnl': 1000.0,
        'total_pnl': 6000.0,
        'pending_orders': 3,
        'timestamp': datetime.now()
    }


@pytest.fixture
def sample_gtt_order_data():
    """Sample GTT order data for testing"""
    return {
        'gtt_id': 'GTT123456',
        'symbol': 'RELIANCE',
        'exchange': 'NSE',
        'trigger_price': 2550.0,
        'target_price': 2600.0,
        'quantity': 10,
        'transaction_type': 'BUY',
        'stop_loss': 2450.0,
        'status': 'ACTIVE',
        'created_at': datetime.now(),
        'triggered_at': None
    }
