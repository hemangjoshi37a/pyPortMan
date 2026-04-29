"""Integration tests for multi-broker support"""

import pytest
from unittest.mock import Mock, patch

from core.client import ZerodhaClient, AngelClient, ClientManager
from core.portfolio import MultiAccountPortfolioManager
from core.orders import OrderManager, OrderType, TransactionType, ProductType


@pytest.mark.integration
class TestMultiBrokerSupport:
    """Integration tests for multi-broker support"""

    @pytest.fixture
    def mock_zerodha_client(self):
        """Mock Zerodha client"""
        with patch('core.client.jugaad_trader') as mock_jugaad:
            mock_instance = Mock()
            mock_instance.login.return_value = True
            mock_instance.profile.return_value = {'user_id': 'ZERODHA123'}
            mock_instance.margins.return_value = {
                'equity': {'available': {'cash': 100000, 'margin_used': 0}},
                'commodity': {'available': {'cash': 50000, 'margin_used': 0}}
            }
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
            mock_instance.positions.return_value = {'day': [], 'net': []}
            mock_instance.orders.return_value = []
            mock_jugaad.Zerodha.return_value = mock_instance

            client = ZerodhaClient('zerodha_account', {
                'user_id': 'ZERODHA123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'totp_key': 'test_totp_key',
                'totp_enabled': True
            })
            client.login()
            return client

    @pytest.fixture
    def mock_angel_client(self):
        """Mock Angel client"""
        with patch('core.client.smartapi') as mock_smartapi:
            mock_instance = Mock()
            mock_instance.generateSession.return_value = {
                'data': {
                    'jwtToken': 'test_token',
                    'refreshToken': 'test_refresh_token'
                }
            }
            mock_instance.getProfile.return_value = {
                'clientcode': 'ANGEL123',
                'name': 'Test User'
            }
            mock_instance.rmsLimit.return_value = {
                'net': {'availablecash': 80000}
            }
            mock_instance.holding.return_value = [
                {
                    'tradingsymbol': 'TCS',
                    'exchange': 'NSE',
                    'quantity': 20,
                    'averageprice': 3400.0,
                    'ltp': 3500.0,
                    'pnl': 2000.0,
                    'daychange': 30.0,
                    'daychangepercentage': 0.88,
                    'product': 'CNC'
                }
            ]
            mock_instance.position.return_value = []
            mock_instance.orderList.return_value = []
            mock_smartapi.SmartConnect.return_value = mock_instance

            client = AngelClient('angel_account', {
                'user_id': 'ANGEL123',
                'password': 'test_password',
                'api_key': 'test_api_key',
                'client_id': 'ANGEL123'
            })
            client.login()
            return client

    @pytest.fixture
    def client_manager(self, mock_zerodha_client, mock_angel_client):
        """Create client manager with multiple clients"""
        manager = ClientManager()
        manager.add_client('zerodha', 'zerodha_account', mock_zerodha_client)
        manager.add_client('angel', 'angel_account', mock_angel_client)
        return manager

    def test_client_manager_initialization(self, client_manager):
        """Test client manager initialization"""
        assert len(client_manager.clients) == 2

    def test_get_client(self, client_manager):
        """Test getting a specific client"""
        client = client_manager.get_client('zerodha', 'zerodha_account')
        assert client is not None
        assert client.broker == 'zerodha'

    def test_get_all_clients(self, client_manager):
        """Test getting all clients"""
        all_clients = client_manager.get_all_clients()
        assert len(all_clients) == 2

    def test_get_authenticated_clients(self, client_manager):
        """Test getting authenticated clients"""
        authenticated = client_manager.get_authenticated_clients()
        assert len(authenticated) == 2

    def test_login_all(self, client_manager):
        """Test logging in all clients"""
        results = client_manager.login_all()
        assert len(results) == 2
        assert all(results.values())

    def test_logout_all(self, client_manager):
        """Test logging out all clients"""
        results = client_manager.logout_all()
        assert len(results) == 2


@pytest.mark.integration
class TestMultiAccountPortfolio:
    """Integration tests for multi-account portfolio management"""

    @pytest.fixture
    def mock_clients(self):
        """Create multiple mock clients"""
        clients = []

        for i in range(3):
            with patch('core.client.jugaad_trader') as mock_jugaad:
                mock_instance = Mock()
                mock_instance.login.return_value = True
                mock_instance.profile.return_value = {'user_id': f'USER{i}'}
                mock_instance.margins.return_value = {
                    'equity': {'available': {'cash': 100000, 'margin_used': 0}},
                    'commodity': {'available': {'cash': 50000, 'margin_used': 0}}
                }
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
                mock_instance.positions.return_value = {'day': [], 'net': []}
                mock_instance.orders.return_value = []
                mock_jugaad.Zerodha.return_value = mock_instance

                client = ZerodhaClient(f'account{i}', {
                    'user_id': f'USER{i}',
                    'password': 'test_password',
                    'api_key': 'test_api_key',
                    'totp_key': 'test_totp_key',
                    'totp_enabled': True
                })
                client.login()
                clients.append(client)

        return clients

    @pytest.fixture
    def multi_portfolio_manager(self, mock_clients):
        """Create multi-account portfolio manager"""
        return MultiAccountPortfolioManager(mock_clients)

    def test_multi_portfolio_initialization(self, multi_portfolio_manager):
        """Test multi-account portfolio manager initialization"""
        assert len(multi_portfolio_manager.portfolio_managers) == 3

    def test_get_consolidated_holdings(self, multi_portfolio_manager):
        """Test getting consolidated holdings"""
        consolidated = multi_portfolio_manager.get_consolidated_holdings()
        assert len(consolidated) == 3  # 3 accounts

    def test_get_consolidated_positions(self, multi_portfolio_manager):
        """Test getting consolidated positions"""
        consolidated = multi_portfolio_manager.get_consolidated_positions()
        assert isinstance(consolidated, list)

    def test_get_consolidated_summary(self, multi_portfolio_manager):
        """Test getting consolidated summary"""
        summary = multi_portfolio_manager.get_consolidated_summary()
        assert 'total_funds' in summary
        assert 'total_holdings_value' in summary
        assert 'total_positions_value' in summary

    def test_get_total_funds(self, multi_portfolio_manager):
        """Test getting total funds"""
        total_funds = multi_portfolio_manager.get_total_funds()
        assert total_funds == 450000.0  # 3 accounts * 150000


@pytest.mark.integration
class TestMultiBrokerOrderPlacement:
    """Integration tests for multi-broker order placement"""

    @pytest.fixture
    def mock_clients(self):
        """Create multiple mock clients for order testing"""
        clients = []

        for i in range(2):
            with patch('core.client.jugaad_trader') as mock_jugaad:
                mock_instance = Mock()
                mock_instance.login.return_value = True
                mock_instance.profile.return_value = {'user_id': f'USER{i}'}
                mock_instance.place_order.return_value = {
                    'order_id': f'ORD{i}123456',
                    'status': 'OPEN'
                }
                mock_instance.orders.return_value = []
                mock_jugaad.Zerodha.return_value = mock_instance

                client = ZerodhaClient(f'account{i}', {
                    'user_id': f'USER{i}',
                    'password': 'test_password',
                    'api_key': 'test_api_key',
                    'totp_key': 'test_totp_key',
                    'totp_enabled': True
                })
                client.login()
                clients.append(client)

        return clients

    def test_place_order_single_account(self, mock_clients):
        """Test placing order on single account"""
        order_manager = OrderManager(mock_clients[0])

        order = order_manager.place_order(
            symbol='RELIANCE',
            exchange='NSE',
            transaction_type=TransactionType.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=2500.0,
            product=ProductType.CNC
        )

        assert order.order_id == 'ORD0123456'

    def test_place_order_multiple_accounts(self, mock_clients):
        """Test placing order on multiple accounts"""
        order_ids = []

        for client in mock_clients:
            order_manager = OrderManager(client)
            order = order_manager.place_order(
                symbol='RELIANCE',
                exchange='NSE',
                transaction_type=TransactionType.BUY,
                order_type=OrderType.LIMIT,
                quantity=10,
                price=2500.0,
                product=ProductType.CNC
            )
            order_ids.append(order.order_id)

        assert len(order_ids) == 2
        assert 'ORD0123456' in order_ids
        assert 'ORD1123456' in order_ids


@pytest.mark.integration
class TestMultiBrokerMarketData:
    """Integration tests for multi-broker market data"""

    @pytest.fixture
    def mock_clients(self):
        """Create multiple mock clients for market data testing"""
        clients = []

        for i in range(2):
            with patch('core.client.jugaad_trader') as mock_jugaad:
                mock_instance = Mock()
                mock_instance.login.return_value = True
                mock_instance.profile.return_value = {'user_id': f'USER{i}'}
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
                mock_jugaad.Zerodha.return_value = mock_instance

                client = ZerodhaClient(f'account{i}', {
                    'user_id': f'USER{i}',
                    'password': 'test_password',
                    'api_key': 'test_api_key',
                    'totp_key': 'test_totp_key',
                    'totp_enabled': True
                })
                client.login()
                clients.append(client)

        return clients

    def test_get_quote_from_multiple_brokers(self, mock_clients):
        """Test getting quote from multiple brokers"""
        from core.market_data import MarketDataManager

        quotes = []
        for client in mock_clients:
            market_data_manager = MarketDataManager(client)
            quote = market_data_manager.get_quote('RELIANCE', 'NSE')
            quotes.append(quote)

        assert len(quotes) == 2
        assert all(q.symbol == 'RELIANCE' for q in quotes)
        assert all(q.last_price == 2500.0 for q in quotes)
