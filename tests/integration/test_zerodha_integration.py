"""Integration tests for Zerodha broker"""

import pytest
import os
from unittest.mock import Mock, patch

from core.client import ZerodhaClient, ClientFactory
from core.orders import OrderManager, OrderType, TransactionType, ProductType
from core.portfolio import PortfolioManager
from core.market_data import MarketDataManager


@pytest.mark.integration
@pytest.mark.requires_api
class TestZerodhaIntegration:
    """Integration tests for Zerodha broker"""

    @pytest.fixture
    def zerodha_credentials(self):
        """Get Zerodha credentials from environment"""
        return {
            'user_id': os.getenv('ZERODHA_USER_ID', 'TEST123'),
            'password': os.getenv('ZERODHA_PASSWORD', 'test_password'),
            'api_key': os.getenv('ZERODHA_API_KEY', 'test_api_key'),
            'totp_key': os.getenv('ZERODHA_TOTP_KEY', 'test_totp_key'),
            'totp_enabled': os.getenv('ZERODHA_TOTP_ENABLED', '1') == '1'
        }

    @pytest.fixture
    def zerodha_client(self, zerodha_credentials):
        """Create Zerodha client"""
        with patch('core.client.jugaad_trader') as mock_jugaad:
            mock_instance = Mock()
            mock_instance.login.return_value = True
            mock_instance.profile.return_value = {'user_id': 'TEST123'}
            mock_instance.margins.return_value = {
                'equity': {'available': {'cash': 100000, 'margin_used': 0}},
                'commodity': {'available': {'cash': 50000, 'margin_used': 0}}
            }
            mock_jugaad.Zerodha.return_value = mock_instance

            client = ZerodhaClient('test_account', zerodha_credentials)
            client.login()
            return client

    def test_zerodha_login(self, zerodha_client):
        """Test Zerodha login"""
        assert zerodha_client.is_authenticated() is True

    def test_zerodha_get_profile(self, zerodha_client):
        """Test getting Zerodha profile"""
        profile = zerodha_client.get_profile()
        assert 'user_id' in profile

    def test_zerodha_check_funds(self, zerodha_client):
        """Test checking Zerodha funds"""
        funds = zerodha_client.check_funds()
        assert 'equity' in funds
        assert 'commodity' in funds

    def test_zerodha_order_manager(self, zerodha_client):
        """Test Zerodha order manager"""
        order_manager = OrderManager(zerodha_client)
        assert order_manager.client is not None

    def test_zerodha_portfolio_manager(self, zerodha_client):
        """Test Zerodha portfolio manager"""
        portfolio_manager = PortfolioManager(zerodha_client)
        assert portfolio_manager.client is not None

    def test_zerodha_market_data_manager(self, zerodha_client):
        """Test Zerodha market data manager"""
        market_data_manager = MarketDataManager(zerodha_client)
        assert market_data_manager.client is not None


@pytest.mark.integration
class TestZerodhaOrderFlow:
    """Integration tests for Zerodha order flow"""

    @pytest.fixture
    def mock_zerodha_client(self):
        """Mock Zerodha client for order flow testing"""
        with patch('core.client.jugaad_trader') as mock_jugaad:
            mock_instance = Mock()
            mock_instance.login.return_value = True
            mock_instance.profile.return_value = {'user_id': 'TEST123'}
            mock_instance.place_order.return_value = {
                'order_id': 'ORD123456',
                'status': 'OPEN'
            }
            mock_instance.cancel_order.return_value = {
                'order_id': 'ORD123456',
                'status': 'CANCELLED'
            }
            mock_instance.modify_order.return_value = {
                'order_id': 'ORD123456',
                'status': 'OPEN',
                'price': 2550.0
            }
            mock_instance.orders.return_value = [
                {'order_id': 'ORD123456', 'status': 'OPEN', 'tradingsymbol': 'RELIANCE'}
            ]
            mock_instance.place_gtt.return_value = {
                'id': 'GTT123456',
                'status': 'ACTIVE'
            }
            mock_instance.delete_gtt.return_value = {
                'id': 'GTT123456',
                'status': 'CANCELLED'
            }
            mock_instance.get_gtts.return_value = [
                {'id': 'GTT123456', 'status': 'ACTIVE', 'tradingsymbol': 'RELIANCE'}
            ]
            mock_jugaad.Zerodha.return_value = mock_instance

            client = ZerodhaClient('test_account', {
                'user_id': 'TEST123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'totp_key': 'test_totp_key',
                'totp_enabled': True
            })
            client.login()
            return client

    def test_place_order(self, mock_zerodha_client):
        """Test placing an order"""
        order_manager = OrderManager(mock_zerodha_client)

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
        assert order.status.value == 'OPEN'

    def test_cancel_order(self, mock_zerodha_client):
        """Test cancelling an order"""
        order_manager = OrderManager(mock_zerodha_client)

        result = order_manager.cancel_order('ORD123456')
        assert result is True

    def test_modify_order(self, mock_zerodha_client):
        """Test modifying an order"""
        order_manager = OrderManager(mock_zerodha_client)

        order = order_manager.modify_order(
            order_id='ORD123456',
            price=2550.0,
            quantity=15
        )

        assert order.price == 2550.0
        assert order.quantity == 15

    def test_get_orders(self, mock_zerodha_client):
        """Test getting orders"""
        order_manager = OrderManager(mock_zerodha_client)

        orders = order_manager.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == 'ORD123456'

    def test_place_gtt_order(self, mock_zerodha_client):
        """Test placing GTT order"""
        order_manager = OrderManager(mock_zerodha_client)

        gtt_order = order_manager.place_gtt_order(
            symbol='RELIANCE',
            exchange='NSE',
            trigger_price=2550.0,
            target_price=2600.0,
            quantity=10,
            transaction_type=TransactionType.BUY
        )

        assert gtt_order.gtt_id == 'GTT123456'
        assert gtt_order.status == 'ACTIVE'

    def test_cancel_gtt_order(self, mock_zerodha_client):
        """Test cancelling GTT order"""
        order_manager = OrderManager(mock_zerodha_client)

        result = order_manager.cancel_gtt_order('GTT123456')
        assert result is True

    def test_get_gtt_orders(self, mock_zerodha_client):
        """Test getting GTT orders"""
        order_manager = OrderManager(mock_zerodha_client)

        gtt_orders = order_manager.get_gtt_orders()
        assert len(gtt_orders) == 1
        assert gtt_orders[0].gtt_id == 'GTT123456'


@pytest.mark.integration
class TestZerodhaPortfolioFlow:
    """Integration tests for Zerodha portfolio flow"""

    @pytest.fixture
    def mock_zerodha_client(self):
        """Mock Zerodha client for portfolio testing"""
        with patch('core.client.jugaad_trader') as mock_jugaad:
            mock_instance = Mock()
            mock_instance.login.return_value = True
            mock_instance.profile.return_value = {'user_id': 'TEST123'}
            mock_instance.holdings.return_value = [
                {
                    'tradingsymbol': 'RELIANCE',
                    'exchange': 'NSE',
                    'quantity': 50,
                    'average_price': 2400.0,
                    'last_price': 2500.0,
                    'pnl': 5000.0,
                    'day_change': 50.0,
                    'day_change_percentage': 2.08,
                    'product': 'CNC'
                }
            ]
            mock_instance.positions.return_value = {
                'day': [
                    {
                        'tradingsymbol': 'TCS',
                        'exchange': 'NSE',
                        'quantity': 10,
                        'buy_price': 3450.0,
                        'sell_price': None,
                        'last_price': 3500.0,
                        'pnl': 500.0,
                        'product': 'MIS',
                        'instrument_type': 'EQ'
                    }
                ],
                'net': []
            }
            mock_instance.margins.return_value = {
                'equity': {'available': {'cash': 100000, 'margin_used': 0}},
                'commodity': {'available': {'cash': 50000, 'margin_used': 0}}
            }
            mock_instance.orders.return_value = [
                {'order_id': 'ORD123456', 'status': 'OPEN'}
            ]
            mock_jugaad.Zerodha.return_value = mock_instance

            client = ZerodhaClient('test_account', {
                'user_id': 'TEST123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'totp_key': 'test_totp_key',
                'totp_enabled': True
            })
            client.login()
            return client

    def test_get_holdings(self, mock_zerodha_client):
        """Test getting holdings"""
        portfolio_manager = PortfolioManager(mock_zerodha_client)

        holdings = portfolio_manager.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].symbol == 'RELIANCE'

    def test_get_positions(self, mock_zerodha_client):
        """Test getting positions"""
        portfolio_manager = PortfolioManager(mock_zerodha_client)

        positions = portfolio_manager.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == 'TCS'

    def test_get_portfolio_summary(self, mock_zerodha_client):
        """Test getting portfolio summary"""
        portfolio_manager = PortfolioManager(mock_zerodha_client)

        summary = portfolio_manager.get_portfolio_summary()
        assert summary.account_name == 'test_account'
        assert summary.broker == 'zerodha'

    def test_calculate_pnl(self, mock_zerodha_client):
        """Test P&L calculation"""
        portfolio_manager = PortfolioManager(mock_zerodha_client)

        pnl = portfolio_manager.calculate_pnl()
        assert 'holdings_pnl' in pnl
        assert 'positions_pnl' in pnl
        assert 'total_pnl' in pnl


@pytest.mark.integration
class TestZerodhaMarketDataFlow:
    """Integration tests for Zerodha market data flow"""

    @pytest.fixture
    def mock_zerodha_client(self):
        """Mock Zerodha client for market data testing"""
        with patch('core.client.jugaad_trader') as mock_jugaad:
            mock_instance = Mock()
            mock_instance.login.return_value = True
            mock_instance.profile.return_value = {'user_id': 'TEST123'}
            mock_instance.quote.return_value = {
                'RELIANCE': {
                    'last_price': 2500.0,
                    'change': 50.0,
                    'change_percent': 2.04,
                    'volume': 1000000,
                    'ohlc': {'open': 2480.0, 'high': 2520.0, 'low': 2470.0, 'close': 2450.0},
                    'depth': {'buy': [{'price': 2499.0}], 'sell': [{'price': 2501.0}]}
                }
            }
            mock_instance.historical_data.return_value = [
                {'date': '2024-01-01', 'open': 2400.0, 'high': 2450.0, 'low': 2380.0, 'close': 2420.0, 'volume': 1000000},
                {'date': '2024-01-02', 'open': 2420.0, 'high': 2470.0, 'low': 2400.0, 'close': 2440.0, 'volume': 1100000}
            ]
            mock_instance.instruments.return_value = [
                {'instrument_token': '123456', 'tradingsymbol': 'RELIANCE', 'exchange': 'NSE'}
            ]
            mock_jugaad.Zerodha.return_value = mock_instance

            client = ZerodhaClient('test_account', {
                'user_id': 'TEST123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'totp_key': 'test_totp_key',
                'totp_enabled': True
            })
            client.login()
            return client

    def test_get_quote(self, mock_zerodha_client):
        """Test getting quote"""
        market_data_manager = MarketDataManager(mock_zerodha_client)

        quote = market_data_manager.get_quote('RELIANCE', 'NSE')
        assert quote.symbol == 'RELIANCE'
        assert quote.last_price == 2500.0

    def test_get_quotes_batch(self, mock_zerodha_client):
        """Test getting batch quotes"""
        market_data_manager = MarketDataManager(mock_zerodha_client)

        # Mock for multiple symbols
        mock_zerodha_client.api.quote.return_value = {
            'RELIANCE': {
                'last_price': 2500.0,
                'change': 50.0,
                'change_percent': 2.04,
                'volume': 1000000,
                'ohlc': {'open': 2480.0, 'high': 2520.0, 'low': 2470.0, 'close': 2450.0},
                'depth': {'buy': [{'price': 2499.0}], 'sell': [{'price': 2501.0}]}
            },
            'TCS': {
                'last_price': 3500.0,
                'change': 70.0,
                'change_percent': 2.04,
                'volume': 500000,
                'ohlc': {'open': 3480.0, 'high': 3520.0, 'low': 3470.0, 'close': 3450.0},
                'depth': {'buy': [{'price': 3499.0}], 'sell': [{'price': 3501.0}]}
            }
        }

        quotes = market_data_manager.get_quotes(['RELIANCE', 'TCS'], 'NSE')
        assert len(quotes) == 2

    def test_get_historical_data(self, mock_zerodha_client):
        """Test getting historical data"""
        market_data_manager = MarketDataManager(mock_zerodha_client)

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

    def test_get_intraday_data(self, mock_zerodha_client):
        """Test getting intraday data"""
        market_data_manager = MarketDataManager(mock_zerodha_client)

        mock_zerodha_client.api.historical_data.return_value = [
            {'date': '2024-01-01 09:15:00', 'open': 2400.0, 'high': 2410.0, 'low': 2395.0, 'close': 2405.0, 'volume': 100000},
            {'date': '2024-01-01 09:30:00', 'open': 2405.0, 'high': 2415.0, 'low': 2400.0, 'close': 2410.0, 'volume': 120000}
        ]

        df = market_data_manager.get_intraday_data('RELIANCE', '15minute', 1, 'NSE')
        assert len(df) > 0
