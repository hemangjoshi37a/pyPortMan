"""
Portfolio Management Module
Handles portfolio tracking, holdings, positions, and P&L calculations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .error_handler import (
    PortfolioError, AuthenticationError, ValidationError,
    with_error_handling, RateLimiter
)
from .logging_config import get_logger
from .client import BrokerClient

logger = get_logger('pyportman.portfolio')


# Enums
class PositionType(Enum):
    """Position type enumeration"""
    LONG = "LONG"
    SHORT = "SHORT"


# Data classes
@dataclass
class Holding:
    """Holding data class"""
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    ltp: float
    pnl: float
    day_change: float = 0.0
    day_change_percent: float = 0.0
    product: str = "CNC"

    @property
    def value(self) -> float:
        """Current value of holding"""
        return self.quantity * self.ltp

    @property
    def investment(self) -> float:
        """Total investment"""
        return self.quantity * self.average_price

    @property
    def pnl_percent(self) -> float:
        """P&L percentage"""
        if self.investment > 0:
            return (self.pnl / self.investment) * 100
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert holding to dictionary"""
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'quantity': self.quantity,
            'average_price': self.average_price,
            'ltp': self.ltp,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'day_change': self.day_change,
            'day_change_percent': self.day_change_percent,
            'value': self.value,
            'investment': self.investment,
            'product': self.product
        }


@dataclass
class Position:
    """Position data class"""
    symbol: str
    exchange: str
    quantity: int
    buy_price: float
    sell_price: float
    ltp: float
    pnl: float
    product: str = "MIS"
    position_type: str = "LONG"

    @property
    def value(self) -> float:
        """Current value of position"""
        return abs(self.quantity) * self.ltp

    @property
    def investment(self) -> float:
        """Total investment"""
        return abs(self.quantity) * self.buy_price

    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary"""
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'quantity': self.quantity,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'ltp': self.ltp,
            'pnl': self.pnl,
            'value': self.value,
            'investment': self.investment,
            'product': self.product,
            'position_type': self.position_type
        }


@dataclass
class PortfolioSummary:
    """Portfolio summary data class"""
    account_name: str
    broker: str
    funds_equity: float
    funds_commodity: float
    total_funds: float
    holdings_count: int
    holdings_value: float
    holdings_pnl: float
    positions_count: int
    positions_value: float
    positions_pnl: float
    total_pnl: float
    pending_orders: int
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_value(self) -> float:
        """Total portfolio value"""
        return self.total_funds + self.holdings_value + self.positions_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary"""
        return {
            'account_name': self.account_name,
            'broker': self.broker,
            'funds_equity': self.funds_equity,
            'funds_commodity': self.funds_commodity,
            'total_funds': self.total_funds,
            'holdings_count': self.holdings_count,
            'holdings_value': self.holdings_value,
            'holdings_pnl': self.holdings_pnl,
            'positions_count': self.positions_count,
            'positions_value': self.positions_value,
            'positions_pnl': self.positions_pnl,
            'total_pnl': self.total_pnl,
            'total_value': self.total_value,
            'pending_orders': self.pending_orders,
            'timestamp': self.timestamp.isoformat()
        }


# Portfolio Manager
class PortfolioManager:
    """
    Manages portfolio data for a broker client
    """

    def __init__(self, client: BrokerClient):
        """
        Initialize portfolio manager

        Args:
            client: Broker client instance
        """
        self.client = client
        self.rate_limiter = RateLimiter(max_calls=30, period=60)

        # Cached data
        self._holdings: Optional[List[Holding]] = None
        self._positions: Optional[List[Position]] = None
        self._last_update: Optional[datetime] = None

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_holdings(self, force_refresh: bool = False) -> List[Holding]:
        """
        Get holdings for the account

        Args:
            force_refresh: Force refresh from API

        Returns:
            List of Holding objects

        Raises:
            PortfolioError: If fetching holdings fails
        """
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        # Return cached data if available and not forcing refresh
        if not force_refresh and self._holdings is not None:
            return self._holdings

        try:
            self.rate_limiter.wait_if_needed(logger=logger)

            if self.client.broker == 'zerodha':
                holdings_data = self.client.api.holdings()
            elif self.client.broker == 'angel':
                holdings_data = self.client.api.holding()['data']
            else:
                raise PortfolioError(f"Get holdings not implemented for broker: {self.client.broker}")

            holdings = []
            for holding_data in holdings_data:
                holdings.append(self._parse_holding(holding_data))

            self._holdings = holdings
            self._last_update = datetime.now()

            logger.info(f"Retrieved {len(holdings)} holdings for {self.client.account_name}")
            return holdings

        except Exception as e:
            raise PortfolioError(f"Failed to get holdings: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_positions(self, force_refresh: bool = False) -> List[Position]:
        """
        Get positions for the account

        Args:
            force_refresh: Force refresh from API

        Returns:
            List of Position objects

        Raises:
            PortfolioError: If fetching positions fails
        """
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        # Return cached data if available and not forcing refresh
        if not force_refresh and self._positions is not None:
            return self._positions

        try:
            self.rate_limiter.wait_if_needed(logger=logger)

            if self.client.broker == 'zerodha':
                positions_data = self.client.api.positions()['net']
            elif self.client.broker == 'angel':
                positions_data = self.client.api.position()['data']
            else:
                raise PortfolioError(f"Get positions not implemented for broker: {self.client.broker}")

            positions = []
            for position_data in positions_data:
                # Filter out closed positions
                if position_data.get('quantity', 0) != 0:
                    positions.append(self._parse_position(position_data))

            self._positions = positions
            self._last_update = datetime.now()

            logger.info(f"Retrieved {len(positions)} positions for {self.client.account_name}")
            return positions

        except Exception as e:
            raise PortfolioError(f"Failed to get positions: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_portfolio_summary(self) -> PortfolioSummary:
        """
        Get consolidated portfolio summary

        Returns:
            PortfolioSummary object

        Raises:
            PortfolioError: If fetching summary fails
        """
        try:
            # Get funds
            funds = self.client.check_funds()

            # Get holdings
            holdings = self.get_holdings()
            holdings_value = sum(h.value for h in holdings)
            holdings_pnl = sum(h.pnl for h in holdings)

            # Get positions
            positions = self.get_positions()
            positions_value = sum(p.value for p in positions)
            positions_pnl = sum(p.pnl for p in positions)

            # Get pending orders count
            from .orders import OrderManager
            order_manager = OrderManager(self.client)
            pending_orders = len(order_manager.get_pending_orders())

            summary = PortfolioSummary(
                account_name=self.client.account_name,
                broker=self.client.broker,
                funds_equity=funds.get('equity', 0),
                funds_commodity=funds.get('commodity', 0),
                total_funds=funds.get('total', 0),
                holdings_count=len(holdings),
                holdings_value=holdings_value,
                holdings_pnl=holdings_pnl,
                positions_count=len(positions),
                positions_value=positions_value,
                positions_pnl=positions_pnl,
                total_pnl=holdings_pnl + positions_pnl,
                pending_orders=pending_orders
            )

            return summary

        except Exception as e:
            raise PortfolioError(f"Failed to get portfolio summary: {str(e)}")

    def calculate_pnl(self) -> Dict[str, float]:
        """
        Calculate total P&L across holdings and positions

        Returns:
            Dictionary with P&L breakdown
        """
        try:
            holdings = self.get_holdings()
            positions = self.get_positions()

            holdings_pnl = sum(h.pnl for h in holdings)
            positions_pnl = sum(p.pnl for p in positions)

            return {
                'holdings_pnl': holdings_pnl,
                'positions_pnl': positions_pnl,
                'total_pnl': holdings_pnl + positions_pnl,
                'holdings_count': len(holdings),
                'positions_count': len(positions)
            }

        except Exception as e:
            logger.error(f"Error calculating P&L: {e}")
            return {
                'holdings_pnl': 0.0,
                'positions_pnl': 0.0,
                'total_pnl': 0.0,
                'holdings_count': 0,
                'positions_count': 0
            }

    def get_sector_allocation(self) -> Dict[str, Dict[str, Any]]:
        """
        Get portfolio allocation by sector

        Returns:
            Dictionary with sector-wise allocation
        """
        try:
            holdings = self.get_holdings()
            sector_allocation = {}

            for holding in holdings:
                sector = self._get_sector_for_symbol(holding.symbol)

                if sector not in sector_allocation:
                    sector_allocation[sector] = {
                        'count': 0,
                        'value': 0.0,
                        'pnl': 0.0,
                        'symbols': []
                    }

                sector_allocation[sector]['count'] += 1
                sector_allocation[sector]['value'] += holding.value
                sector_allocation[sector]['pnl'] += holding.pnl
                sector_allocation[sector]['symbols'].append(holding.symbol)

            return sector_allocation

        except Exception as e:
            logger.error(f"Error getting sector allocation: {e}")
            return {}

    def get_top_performers(self, n: int = 5) -> Dict[str, List[Dict]]:
        """
        Get top performing holdings by P&L

        Args:
            n: Number of top performers to return

        Returns:
            Dictionary with top gainers and losers
        """
        try:
            holdings = self.get_holdings()

            # Sort by P&L
            sorted_holdings = sorted(holdings, key=lambda h: h.pnl, reverse=True)

            top_gainers = [h.to_dict() for h in sorted_holdings[:n]]
            top_losers = [h.to_dict() for h in sorted_holdings[-n:]]

            return {
                'top_gainers': top_gainers,
                'top_losers': top_losers
            }

        except Exception as e:
            logger.error(f"Error getting top performers: {e}")
            return {'top_gainers': [], 'top_losers': []}

    def refresh(self) -> None:
        """Refresh cached portfolio data"""
        self._holdings = None
        self._positions = None
        self._last_update = None
        logger.info(f"Portfolio cache cleared for {self.client.account_name}")

    def _parse_holding(self, holding_data: Dict[str, Any]) -> Holding:
        """Parse holding data from broker API"""
        # Zerodha format
        if 'tradingsymbol' in holding_data:
            return Holding(
                symbol=holding_data.get('tradingsymbol', ''),
                exchange=holding_data.get('exchange', 'NSE'),
                quantity=holding_data.get('quantity', 0),
                average_price=holding_data.get('average_price', 0),
                ltp=holding_data.get('last_price', 0),
                pnl=holding_data.get('pnl', 0),
                day_change=holding_data.get('day_change', 0),
                day_change_percent=holding_data.get('day_change_percentage', 0),
                product=holding_data.get('product', 'CNC')
            )
        # Angel format
        elif 'tradingsymbol' in holding_data or 'symbol' in holding_data:
            return Holding(
                symbol=holding_data.get('tradingsymbol', holding_data.get('symbol', '')),
                exchange=holding_data.get('exchange', 'NSE'),
                quantity=holding_data.get('quantity', 0),
                average_price=holding_data.get('averageprice', holding_data.get('avgprice', 0)),
                ltp=holding_data.get('ltp', 0),
                pnl=holding_data.get('pnl', 0),
                product=holding_data.get('producttype', 'CNC')
            )
        else:
            raise PortfolioError(f"Unknown holding data format: {holding_data}")

    def _parse_position(self, position_data: Dict[str, Any]) -> Position:
        """Parse position data from broker API"""
        # Zerodha format
        if 'tradingsymbol' in position_data:
            return Position(
                symbol=position_data.get('tradingsymbol', ''),
                exchange=position_data.get('exchange', 'NSE'),
                quantity=position_data.get('quantity', 0),
                buy_price=position_data.get('average_price', 0),
                sell_price=position_data.get('last_price', 0),
                ltp=position_data.get('last_price', 0),
                pnl=position_data.get('pnl', 0),
                product=position_data.get('product', 'MIS'),
                position_type='LONG' if position_data.get('quantity', 0) > 0 else 'SHORT'
            )
        # Angel format
        elif 'tradingsymbol' in position_data or 'symbol' in position_data:
            return Position(
                symbol=position_data.get('tradingsymbol', position_data.get('symbol', '')),
                exchange=position_data.get('exchange', 'NSE'),
                quantity=position_data.get('quantity', 0),
                buy_price=position_data.get('averageprice', position_data.get('buyprice', 0)),
                sell_price=position_data.get('sellprice', 0),
                ltp=position_data.get('ltp', 0),
                pnl=position_data.get('pnl', 0),
                product=position_data.get('producttype', 'MIS'),
                position_type='LONG' if position_data.get('quantity', 0) > 0 else 'SHORT'
            )
        else:
            raise PortfolioError(f"Unknown position data format: {position_data}")

    def _get_sector_for_symbol(self, symbol: str) -> str:
        """Get sector for a given symbol"""
        # Simplified sector mapping
        sector_map = {
            # IT
            'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'HCLTECH': 'IT', 'TECHM': 'IT',
            # Banking
            'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking',
            'AXISBANK': 'Banking', 'KOTAKBANK': 'Banking', 'INDUSINDBK': 'Banking',
            # Finance
            'BAJFINANCE': 'Finance', 'HDFC': 'Finance', 'BAJAJFINSV': 'Finance',
            # FMCG
            'ITC': 'FMCG', 'HINDUNILVR': 'FMCG', 'NESTLEIND': 'FMCG', 'BRITANNIA': 'FMCG',
            # Auto
            'TATAMOTORS': 'Auto', 'MARUTI': 'Auto', 'M&M': 'Auto', 'EICHERMOT': 'Auto',
            # Energy
            'RELIANCE': 'Energy', 'ONGC': 'Energy', 'GAIL': 'Energy',
            # Pharma
            'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma',
            # Metals
            'TATASTEEL': 'Metals', 'JSWSTEEL': 'Metals', 'HINDALCO': 'Metals',
            # Telecom
            'BHARTIARTL': 'Telecom',
            # Infrastructure
            'LT': 'Infrastructure', 'POWERGRID': 'Power',
        }

        return sector_map.get(symbol, 'Others')


# Multi-Account Portfolio Manager
class MultiAccountPortfolioManager:
    """
    Manages portfolio across multiple accounts
    """

    def __init__(self, clients: List[BrokerClient]):
        """
        Initialize multi-account portfolio manager

        Args:
            clients: List of broker client instances
        """
        self.clients = clients
        self.portfolio_managers = {
            f"{client.broker}_{client.account_name}": PortfolioManager(client)
            for client in clients
        }

    def get_consolidated_holdings(self) -> Dict[str, Any]:
        """
        Get consolidated holdings across all accounts

        Returns:
            Dictionary with consolidated holdings data
        """
        consolidated = {
            'total_holdings': [],
            'by_account': {},
            'summary': {
                'total_value': 0.0,
                'total_pnl': 0.0,
                'total_count': 0,
                'unique_symbols': set()
            }
        }

        for key, manager in self.portfolio_managers.items():
            try:
                holdings = manager.get_holdings()

                account_holdings = {
                    'account_name': manager.client.account_name,
                    'broker': manager.client.broker,
                    'holdings': []
                }

                for holding in holdings:
                    holding_data = holding.to_dict()
                    holding_data['account'] = manager.client.account_name
                    account_holdings['holdings'].append(holding_data)
                    consolidated['total_holdings'].append(holding_data)

                    # Update summary
                    consolidated['summary']['total_value'] += holding.value
                    consolidated['summary']['total_pnl'] += holding.pnl
                    consolidated['summary']['total_count'] += 1
                    consolidated['summary']['unique_symbols'].add(holding.symbol)

                consolidated['by_account'][key] = account_holdings

            except Exception as e:
                logger.error(f"Error getting holdings for {key}: {e}")

        # Convert set to list
        consolidated['summary']['unique_symbols'] = list(consolidated['summary']['unique_symbols'])

        return consolidated

    def get_consolidated_positions(self) -> Dict[str, Any]:
        """
        Get consolidated positions across all accounts

        Returns:
            Dictionary with consolidated positions data
        """
        consolidated = {
            'total_positions': [],
            'by_account': {},
            'summary': {
                'total_value': 0.0,
                'total_pnl': 0.0,
                'total_count': 0,
                'unique_symbols': set()
            }
        }

        for key, manager in self.portfolio_managers.items():
            try:
                positions = manager.get_positions()

                account_positions = {
                    'account_name': manager.client.account_name,
                    'broker': manager.client.broker,
                    'positions': []
                }

                for position in positions:
                    position_data = position.to_dict()
                    position_data['account'] = manager.client.account_name
                    account_positions['positions'].append(position_data)
                    consolidated['total_positions'].append(position_data)

                    # Update summary
                    consolidated['summary']['total_value'] += position.value
                    consolidated['summary']['total_pnl'] += position.pnl
                    consolidated['summary']['total_count'] += 1
                    consolidated['summary']['unique_symbols'].add(position.symbol)

                consolidated['by_account'][key] = account_positions

            except Exception as e:
                logger.error(f"Error getting positions for {key}: {e}")

        # Convert set to list
        consolidated['summary']['unique_symbols'] = list(consolidated['summary']['unique_symbols'])

        return consolidated

    def get_consolidated_summary(self) -> Dict[str, Any]:
        """
        Get consolidated portfolio summary across all accounts

        Returns:
            Dictionary with consolidated summary
        """
        summary = {
            'total_accounts': len(self.clients),
            'total_funds': 0.0,
            'total_holdings_value': 0.0,
            'total_positions_value': 0.0,
            'total_pnl': 0.0,
            'total_holdings_count': 0,
            'total_positions_count': 0,
            'by_account': {}
        }

        for key, manager in self.portfolio_managers.items():
            try:
                portfolio_summary = manager.get_portfolio_summary()
                summary_dict = portfolio_summary.to_dict()

                summary['by_account'][key] = summary_dict

                summary['total_funds'] += summary_dict['total_funds']
                summary['total_holdings_value'] += summary_dict['holdings_value']
                summary['total_positions_value'] += summary_dict['positions_value']
                summary['total_pnl'] += summary_dict['total_pnl']
                summary['total_holdings_count'] += summary_dict['holdings_count']
                summary['total_positions_count'] += summary_dict['positions_count']

            except Exception as e:
                logger.error(f"Error getting summary for {key}: {e}")

        return summary

    def get_total_funds(self) -> Dict[str, Any]:
        """
        Get total funds across all accounts

        Returns:
            Dictionary with total funds breakdown
        """
        total_funds = {
            'total_equity': 0.0,
            'total_commodity': 0.0,
            'grand_total': 0.0,
            'by_account': {},
            'by_broker': {}
        }

        for key, manager in self.portfolio_managers.items():
            try:
                funds = manager.client.check_funds()

                account_funds = {
                    'account_name': manager.client.account_name,
                    'broker': manager.client.broker,
                    'equity': funds.get('equity', 0),
                    'commodity': funds.get('commodity', 0),
                    'total': funds.get('total', 0)
                }

                total_funds['by_account'][key] = account_funds

                # Update totals
                total_funds['total_equity'] += funds.get('equity', 0)
                total_funds['total_commodity'] += funds.get('commodity', 0)

                # Update broker-wise totals
                broker = manager.client.broker
                if broker not in total_funds['by_broker']:
                    total_funds['by_broker'][broker] = {
                        'equity': 0.0,
                        'commodity': 0.0,
                        'count': 0
                    }

                total_funds['by_broker'][broker]['equity'] += funds.get('equity', 0)
                total_funds['by_broker'][broker]['commodity'] += funds.get('commodity', 0)
                total_funds['by_broker'][broker]['count'] += 1

            except Exception as e:
                logger.error(f"Error getting funds for {key}: {e}")

        total_funds['grand_total'] = total_funds['total_equity'] + total_funds['total_commodity']

        return total_funds
