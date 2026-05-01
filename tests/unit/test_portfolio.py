"""Unit tests for portfolio module"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from core.portfolio import (
    Holding,
    Position,
    PortfolioSummary,
    PortfolioManager,
    MultiAccountPortfolioManager
)


class TestHolding:
    """Test Holding dataclass"""

    def test_holding_creation(self):
        """Test creating a Holding"""
        holding = Holding(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=50,
            average_price=2400.0,
            ltp=2500.0,
            pnl=5000.0,
            day_change=50.0,
            day_change_percent=2.08,
            product='CNC'
        )

        assert holding.symbol == 'RELIANCE'
        assert holding.quantity == 50
        assert holding.average_price == 2400.0

    def test_holding_value(self):
        """Test holding value calculation"""
        holding = Holding(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=50,
            average_price=2400.0,
            ltp=2500.0,
            pnl=5000.0,
            day_change=50.0,
            day_change_percent=2.08,
            product='CNC'
        )

        assert holding.value == 125000.0  # 50 * 2500

    def test_holding_investment(self):
        """Test holding investment calculation"""
        holding = Holding(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=50,
            average_price=2400.0,
            ltp=2500.0,
            pnl=5000.0,
            day_change=50.0,
            day_change_percent=2.08,
            product='CNC'
        )

        assert holding.investment == 120000.0  # 50 * 2400

    def test_holding_pnl_percent(self):
        """Test holding P&L percent calculation"""
        holding = Holding(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=50,
            average_price=2400.0,
            ltp=2500.0,
            pnl=5000.0,
            day_change=50.0,
            day_change_percent=2.08,
            product='CNC'
        )

        expected = (5000.0 / 120000.0) * 100
        assert abs(holding.pnl_percent - expected) < 0.01

    def test_holding_to_dict(self):
        """Test converting Holding to dict"""
        holding = Holding(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=50,
            average_price=2400.0,
            ltp=2500.0,
            pnl=5000.0,
            day_change=50.0,
            day_change_percent=2.08,
            product='CNC'
        )

        result = holding.to_dict()
        assert isinstance(result, dict)
        assert result['symbol'] == 'RELIANCE'
        assert result['quantity'] == 50


class TestPosition:
    """Test Position dataclass"""

    def test_position_creation(self):
        """Test creating a Position"""
        position = Position(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=10,
            buy_price=2450.0,
            sell_price=None,
            ltp=2500.0,
            pnl=500.0,
            product='MIS',
            position_type='LONG'
        )

        assert position.symbol == 'RELIANCE'
        assert position.quantity == 10
        assert position.position_type == 'LONG'

    def test_position_value(self):
        """Test position value calculation"""
        position = Position(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=10,
            buy_price=2450.0,
            sell_price=None,
            ltp=2500.0,
            pnl=500.0,
            product='MIS',
            position_type='LONG'
        )

        assert position.value == 25000.0  # 10 * 2500

    def test_position_investment(self):
        """Test position investment calculation"""
        position = Position(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=10,
            buy_price=2450.0,
            sell_price=None,
            ltp=2500.0,
            pnl=500.0,
            product='MIS',
            position_type='LONG'
        )

        assert position.investment == 24500.0  # 10 * 2450

    def test_position_to_dict(self):
        """Test converting Position to dict"""
        position = Position(
            symbol='RELIANCE',
            exchange='NSE',
            quantity=10,
            buy_price=2450.0,
            sell_price=None,
            ltp=2500.0,
            pnl=500.0,
            product='MIS',
            position_type='LONG'
        )

        result = position.to_dict()
        assert isinstance(result, dict)
        assert result['symbol'] == 'RELIANCE'
        assert result['quantity'] == 10


class TestPortfolioSummary:
    """Test PortfolioSummary dataclass"""

    def test_portfolio_summary_creation(self):
        """Test creating PortfolioSummary"""
        summary = PortfolioSummary(
            account_name='test_account',
            broker='zerodha',
            funds_equity=100000.0,
            funds_commodity=50000.0,
            total_funds=150000.0,
            holdings_count=5,
            holdings_value=75000.0,
            holdings_pnl=5000.0,
            positions_count=2,
            positions_value=25000.0,
            positions_pnl=1000.0,
            total_pnl=6000.0,
            pending_orders=3,
            timestamp=datetime.now()
        )

        assert summary.account_name == 'test_account'
        assert summary.total_funds == 150000.0

    def test_portfolio_summary_total_value(self):
        """Test total value calculation"""
        summary = PortfolioSummary(
            account_name='test_account',
            broker='zerodha',
            funds_equity=100000.0,
            funds_commodity=50000.0,
            total_funds=150000.0,
            holdings_count=5,
            holdings_value=75000.0,
            holdings_pnl=5000.0,
            positions_count=2,
            positions_value=25000.0,
            positions_pnl=1000.0,
            total_pnl=6000.0,
            pending_orders=3,
            timestamp=datetime.now()
        )

        expected = 150000.0 + 75000.0 + 25000.0
        assert summary.total_value == expected

    def test_portfolio_summary_to_dict(self):
        """Test converting PortfolioSummary to dict"""
        summary = PortfolioSummary(
            account_name='test_account',
            broker='zerodha',
            funds_equity=100000.0,
            funds_commodity=50000.0,
            total_funds=150000.0,
            holdings_count=5,
            holdings_value=75000.0,
            holdings_pnl=5000.0,
            positions_count=2,
            positions_value=25000.0,
            positions_pnl=1000.0,
            total_pnl=6000.0,
            pending_orders=3,
            timestamp=datetime.now()
        )

        result = summary.to_dict()
        assert isinstance(result, dict)
        assert result['account_name'] == 'test_account'
        assert result['total_funds'] == 150000.0


class TestPortfolioManager:
    """Test PortfolioManager class"""

    @pytest.fixture
    def mock_client(self):
        """Mock broker client"""
        client = Mock()
        client.broker = 'zerodha'
        client.account_name = 'test_account'
        client._authenticated = True
        return client

    @pytest.fixture
    def portfolio_manager(self, mock_client):
        """Create PortfolioManager instance"""
        return PortfolioManager(mock_client)

    def test_initialization(self, portfolio_manager):
        """Test PortfolioManager initialization"""
        assert portfolio_manager.client is not None
        assert portfolio_manager._rate_limiter is not None
        assert portfolio_manager._holdings is None
        assert portfolio_manager._positions is None

    def test_get_holdings(self, portfolio_manager):
        """Test getting holdings"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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

        holdings = portfolio_manager.get_holdings()

        assert len(holdings) == 1
        assert holdings[0].symbol == 'RELIANCE'
        assert holdings[0].quantity == 50

    def test_get_holdings_cached(self, portfolio_manager):
        """Test that holdings are cached"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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

        # First call
        holdings1 = portfolio_manager.get_holdings()
        # Second call - should use cache
        holdings2 = portfolio_manager.get_holdings()

        assert holdings1 == holdings2
        # API should be called only once
        assert portfolio_manager.client.api.holdings.call_count == 1

    def test_get_holdings_force_refresh(self, portfolio_manager):
        """Test force refresh of holdings"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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

        # First call
        portfolio_manager.get_holdings()
        # Force refresh
        portfolio_manager.get_holdings(force_refresh=True)

        # API should be called twice
        assert portfolio_manager.client.api.holdings.call_count == 2

    def test_get_positions(self, portfolio_manager):
        """Test getting positions"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.positions.return_value = {
            'day': [
                {
                    'tradingsymbol': 'RELIANCE',
                    'exchange': 'NSE',
                    'quantity': 10,
                    'buy_price': 2450.0,
                    'sell_price': None,
                    'last_price': 2500.0,
                    'pnl': 500.0,
                    'product': 'MIS',
                    'instrument_type': 'EQ'
                }
            ],
            'net': []
        }

        positions = portfolio_manager.get_positions()

        assert len(positions) == 1
        assert positions[0].symbol == 'RELIANCE'

    def test_get_portfolio_summary(self, portfolio_manager):
        """Test getting portfolio summary"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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
        portfolio_manager.client.api.positions.return_value = {
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
        portfolio_manager.client.api.margins.return_value = {
            'equity': {'available': {'cash': 100000, 'margin_used': 0}},
            'commodity': {'available': {'cash': 50000, 'margin_used': 0}}
        }
        portfolio_manager.client.api.orders.return_value = [
            {'order_id': 'ORD123456', 'status': 'OPEN'}
        ]

        summary = portfolio_manager.get_portfolio_summary()

        assert summary.account_name == 'test_account'
        assert summary.broker == 'zerodha'
        assert summary.funds_equity == 100000.0
        assert summary.funds_commodity == 50000.0

    def test_calculate_pnl(self, portfolio_manager):
        """Test P&L calculation"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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
        portfolio_manager.client.api.positions.return_value = {
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

        pnl = portfolio_manager.calculate_pnl()

        assert pnl['holdings_pnl'] == 5000.0
        assert pnl['positions_pnl'] == 500.0
        assert pnl['total_pnl'] == 5500.0

    def test_get_sector_allocation(self, portfolio_manager):
        """Test sector allocation"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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
            },
            {
                'tradingsymbol': 'TCS',
                'exchange': 'NSE',
                'quantity': 20,
                'average_price': 3400.0,
                'last_price': 3500.0,
                'pnl': 2000.0,
                'day_change': 30.0,
                'day_change_percentage': 0.88,
                'product': 'CNC'
            }
        ]

        allocation = portfolio_manager.get_sector_allocation()

        assert 'Energy' in allocation  # RELIANCE
        assert 'IT' in allocation  # TCS

    def test_get_top_performers(self, portfolio_manager):
        """Test getting top performers"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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
            },
            {
                'tradingsymbol': 'TCS',
                'exchange': 'NSE',
                'quantity': 20,
                'average_price': 3400.0,
                'last_price': 3300.0,
                'pnl': -2000.0,
                'day_change': -30.0,
                'day_change_percentage': -0.88,
                'product': 'CNC'
            }
        ]

        performers = portfolio_manager.get_top_performers(n=5)

        assert 'gainers' in performers
        assert 'losers' in performers
        assert len(performers['gainers']) > 0
        assert len(performers['losers']) > 0

    def test_refresh(self, portfolio_manager):
        """Test refresh clears cache"""
        portfolio_manager.client.api = Mock()
        portfolio_manager.client.api.holdings.return_value = [
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

        # Get holdings to populate cache
        portfolio_manager.get_holdings()
        assert portfolio_manager._holdings is not None

        # Refresh
        portfolio_manager.refresh()
        assert portfolio_manager._holdings is None
        assert portfolio_manager._positions is None


class TestMultiAccountPortfolioManager:
    """Test MultiAccountPortfolioManager class"""

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients"""
        client1 = Mock()
        client1.broker = 'zerodha'
        client1.account_name = 'account1'
        client1._authenticated = True

        client2 = Mock()
        client2.broker = 'zerodha'
        client2.account_name = 'account2'
        client2._authenticated = True

        return [client1, client2]

    @pytest.fixture
    def multi_manager(self, mock_clients):
        """Create MultiAccountPortfolioManager instance"""
        return MultiAccountPortfolioManager(mock_clients)

    def test_initialization(self, multi_manager):
        """Test MultiAccountPortfolioManager initialization"""
        assert len(multi_manager.portfolio_managers) == 2

    def test_get_consolidated_holdings(self, multi_manager):
        """Test getting consolidated holdings"""
        # Mock the portfolio managers
        for pm in multi_manager.portfolio_managers:
            pm.get_holdings.return_value = [
                Holding(
                    symbol='RELIANCE',
                    exchange='NSE',
                    quantity=50,
                    average_price=2400.0,
                    ltp=2500.0,
                    pnl=5000.0,
                    day_change=50.0,
                    day_change_percent=2.08,
                    product='CNC'
                )
            ]

        consolidated = multi_manager.get_consolidated_holdings()

        assert len(consolidated) == 2  # 2 accounts

    def test_get_consolidated_positions(self, multi_manager):
        """Test getting consolidated positions"""
        for pm in multi_manager.portfolio_managers:
            pm.get_positions.return_value = [
                Position(
                    symbol='TCS',
                    exchange='NSE',
                    quantity=10,
                    buy_price=3450.0,
                    sell_price=None,
                    ltp=3500.0,
                    pnl=500.0,
                    product='MIS',
                    position_type='LONG'
                )
            ]

        consolidated = multi_manager.get_consolidated_positions()

        assert len(consolidated) == 2

    def test_get_consolidated_summary(self, multi_manager):
        """Test getting consolidated summary"""
        for pm in multi_manager.portfolio_managers:
            pm.get_portfolio_summary.return_value = PortfolioSummary(
                account_name='test',
                broker='zerodha',
                funds_equity=100000.0,
                funds_commodity=50000.0,
                total_funds=150000.0,
                holdings_count=5,
                holdings_value=75000.0,
                holdings_pnl=5000.0,
                positions_count=2,
                positions_value=25000.0,
                positions_pnl=1000.0,
                total_pnl=6000.0,
                pending_orders=3,
                timestamp=datetime.now()
            )

        summary = multi_manager.get_consolidated_summary()

        assert summary['total_funds'] == 300000.0  # 2 * 150000
        assert summary['total_holdings_value'] == 150000.0  # 2 * 75000

    def test_get_total_funds(self, multi_manager):
        """Test getting total funds"""
        for pm in multi_manager.portfolio_managers:
            pm.get_portfolio_summary.return_value = PortfolioSummary(
                account_name='test',
                broker='zerodha',
                funds_equity=100000.0,
                funds_commodity=50000.0,
                total_funds=150000.0,
                holdings_count=5,
                holdings_value=75000.0,
                holdings_pnl=5000.0,
                positions_count=2,
                positions_value=25000.0,
                positions_pnl=1000.0,
                total_pnl=6000.0,
                pending_orders=3,
                timestamp=datetime.now()
            )

        total_funds = multi_manager.get_total_funds()

        assert total_funds == 300000.0
