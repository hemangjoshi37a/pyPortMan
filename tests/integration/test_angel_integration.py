"""Integration tests for Angel broker"""

import pytest
import os
from unittest.mock import Mock, patch

from core.client import AngelClient
from core.orders import OrderManager, OrderType, TransactionType, ProductType
from core.portfolio import PortfolioManager
from core.market_data import MarketDataManager


@pytest.mark.integration
@pytest.mark.requires_api
class TestAngelIntegration:
    """Integration tests for Angel broker"""

    @pytest.fixture
    def angel_credentials(self):
        """Get Angel credentials from environment"""
        return {
            'user_id': os.getenv('ANGEL_USER_ID', 'TEST123'),
            'password': os.getenv('ANGEL_PASSWORD', 'test_password'),
            'api_key': os.getenv('ANGEL_API_KEY', 'test_api_key'),
            'client_id': os.getenv('ANGEL_CLIENT_ID', 'TEST123')
        }

    @pytest.fixture
    def angel_client(self, angel_credentials):
        """Create Angel client"""
        with patch('core.client.smartapi') as mock_smartapi:
            mock_instance = Mock()
            mock_instance.generateSession.return_value = {
                'data': {
                    'jwtToken': 'test_token',
                    'refreshToken': 'test_refresh_token'
                }
            }
            mock_instance.getProfile.return_value = {
                'clientcode': 'TEST123',
                'name': 'Test User'
            }
            mock_instance.rmsLimit.return_value = {
                'net': {'availablecash': 100000}
            }
            mock_smartapi.SmartConnect.return_value = mock_instance

            client = AngelClient('test_account', angel_credentials)
            client.login()
            return client

    def test_angel_login(self, angel_client):
        """Test Angel login"""
        assert angel_client.is_authenticated() is True

    def test_angel_get_profile(self, angel_client):
        """Test getting Angel profile"""
        profile = angel_client.get_profile()
        assert 'clientcode' in profile

    def test_angel_check_funds(self, angel_client):
        """Test checking Angel funds"""
        funds = angel_client.check_funds()
        assert funds == 100000

    def test_angel_order_manager(self, angel_client):
        """Test Angel order manager"""
        order_manager = OrderManager(angel_client)
        assert order_manager.client is not None

    def test_angel_portfolio_manager(self, angel_client):
        """Test Angel portfolio manager"""
        portfolio_manager = PortfolioManager(angel_client)
        assert portfolio_manager.client is not None

    def test_angel_market_data_manager(self, angel_client):
        """Test Angel market data manager"""
        market_data_manager = MarketDataManager(angel_client)
        assert market_data_manager.client is not None


@pytest.mark.integration
class TestAngelOrderFlow:
    """Integration tests for Angel order flow"""

    @pytest.fixture
    def mock_angel_client(self):
        """Mock Angel client for order flow testing"""
        with patch('core.client.smartapi') as mock_smartapi:
            mock_instance = Mock()
            mock_instance.generateSession.return_value = {
                'data': {
                    'jwtToken': 'test_token',
                    'refreshToken': 'test_refresh_token'
                }
            }
            mock_instance.order.return_value = {
                'orderid': 'ORD123456',
                'status': 'open'
            }
            mock_instance.cancelOrder.return_value = {
                'orderid': 'ORD123456',
                'status': 'cancelled'
            }
            mock_instance.modifyOrder.return_value = {
                'orderid': 'ORD123456',
                'status': 'open',
                'price': 2550.0
            }
            mock_instance.orderList.return_value = [
                {'orderid': 'ORD123456', 'status': 'open', 'tradingsymbol': 'RELIANCE'}
            ]
            mock_smartapi.SmartConnect.return_value = mock_instance

            client = AngelClient('test_account', {
                'user_id': 'TEST123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'client_id': 'TEST123'
            })
            client.login()
            return client

    def test_place_order(self, mock_angel_client):
        """Test placing an order"""
        order_manager = OrderManager(mock_angel_client)

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

    def test_cancel_order(self, mock_angel_client):
        """Test cancelling an order"""
        order_manager = OrderManager(mock_angel_client)

        result = order_manager.cancel_order('ORD123456')
        assert result is True

    def test_modify_order(self, mock_angel_client):
        """Test modifying an order"""
        order_manager = OrderManager(mock_angel_client)

        order = order_manager.modify_order(
            order_id='ORD123456',
            price=2550.0,
            quantity=15
        )

        assert order.price == 2550.0
        assert order.quantity == 15

    def test_get_orders(self, mock_angel_client):
        """Test getting orders"""
        order_manager = OrderManager(mock_angel_client)

        orders = order_manager.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == 'ORD123456'


@pytest.mark.integration
class TestAngelPortfolioFlow:
    """Integration tests for Angel portfolio flow"""

    @pytest.fixture
    def mock_angel_client(self):
        """Mock Angel client for portfolio testing"""
        with patch('core.client.smartapi') as mock_smartapi:
            mock_instance = Mock()
            mock_instance.generateSession.return_value = {
                'data': {
                    'jwtToken': 'test_token',
                    'refreshToken': 'test_refresh_token'
                }
            }
            mock_instance.holding.return_value = [
                {
                    'tradingsymbol': 'RELIANCE',
                    'exchange': 'NSE',
                    'quantity': 50,
                    'averageprice': 2400.0,
                    'ltp': 2500.0,
                    'pnl': 5000.0,
                    'daychange': 50.0,
                    'daychangepercentage': 2.08,
                    'product': 'CNC'
                }
            ]
            mock_instance.position.return_value = [
                {
                    'tradingsymbol': 'TCS',
                    'exchange': 'NSE',
                    'quantity': 10,
                    'buyprice': 3450.0,
                    'sellprice': None,
                    'ltp': 3500.0,
                    'pnl': 500.0,
                    'product': 'MIS',
                    'instrumenttype': 'EQ'
                }
            ]
            mock_instance.rmsLimit.return_value = {
                'net': {'availablecash': 100000}
            }
            mock_instance.orderList.return_value = [
                {'orderid': 'ORD123456', 'status': 'open'}
            ]
            mock_smartapi.SmartConnect.return_value = mock_instance

            client = AngelClient('test_account', {
                'user_id': 'TEST123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'client_id': 'TEST123'
            })
            client.login()
            return client

    def test_get_holdings(self, mock_angel_client):
        """Test getting holdings"""
        portfolio_manager = PortfolioManager(mock_angel_client)

        holdings = portfolio_manager.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].symbol == 'RELIANCE'

    def test_get_positions(self, mock_angel_client):
        """Test getting positions"""
        portfolio_manager = PortfolioManager(mock_angel_client)

        positions = portfolio_manager.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == 'TCS'

    def test_get_portfolio_summary(self, mock_angel_client):
        """Test getting portfolio summary"""
        portfolio_manager = PortfolioManager(mock_angel_client)

        summary = portfolio_manager.get_portfolio_summary()
        assert summary.account_name == 'test_account'
        assert summary.broker == 'angel'


@pytest.mark.integration
class TestAngelMarketDataFlow:
    """Integration tests for Angel market data flow"""

    @pytest.fixture
    def mock_angel_client(self):
        """Mock Angel client for market data testing"""
        with patch('core.client.smartapi') as mock_smartapi:
            mock_instance = Mock()
            mock_instance.generateSession.return_value = {
                'data': {
                    'jwtToken': 'test_token',
                    'refreshToken': 'test_refresh_token'
                }
            }
            mock_instance.ltpData.return_value = {
                'data': {
                    'RELIANCE': {
                        'ltp': 2500.0,
                        'change': 50.0,
                        'change_percent': 2.04,
                        'volume': 1000000,
                        'ohlc': {'open': 2480.0, 'high': 2520.0, 'low': 2470.0, 'close': 2450.0}
                    }
                }
            }
            mock_instance.getCandleData.return_value = [
                [1704067200000, 2400.0, 2450.0, 2380.0, 2420.0, 1000000],
                [1704153600000, 2420.0, 2470.0, 2400.0, 2440.0, 1100000]
            ]
            mock_instance.searchScrip.return_value = [
                {'symboltoken': '123456', 'tradingsymbol': 'RELIANCE', 'exchange': 'NSE'}
            ]
            mock_smartapi.SmartConnect.return_value = mock_instance

            client = AngelClient('test_account', {
                'user_id': 'TEST123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'client_id': 'TEST123'
            })
            client.login()
            return client

    def test_get_quote(self, mock_angel_client):
        """Test getting quote"""
        market_data_manager = MarketDataManager(mock_angel_client)

        quote = market_data_manager.get_quote('RELIANCE', 'NSE')
        assert quote.symbol == 'RELIANCE'
        assert quote.last_price == 2500.0

    def test_get_historical_data(self, mock_angel_client):
        """Test getting historical data"""
        market_data_manager = MarketDataManager(mock_angel_client)

        df = market_data_manager.get_historical_data(
            'RELIANCE',
            '2024-01-01',
            '2024-01-02',
            'day',
            'NSE'
        )

        assert len(df) == 2
        assert 'open' in df.columns
        assert 'close' in df.columns
