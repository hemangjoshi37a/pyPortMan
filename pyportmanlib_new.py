"""
pyPortMan - Python Portfolio Management System
Main module with backward compatibility and new architecture

This module provides the main interface for pyPortMan while using the new
core modules for improved architecture, error handling, and security.
"""

import pandas as pd
import datetime
from typing import List, Dict, Any, Optional

# Import new core modules
from core.client import (
    BrokerClient, ZerodhaClient, AngelClient,
    ClientFactory, ClientManager
)
from core.orders import (
    OrderManager, Order, GTTOrder,
    OrderType, TransactionType, ProductType, Exchange, OrderValidity
)
from core.portfolio import (
    PortfolioManager, MultiAccountPortfolioManager,
    Holding, Position, PortfolioSummary
)
from core.market_data import (
    MarketDataManager, Quote, OHLCV, MarketDataUtils
)
from core.error_handler import (
    PyPortManError, AuthenticationError, OrderError,
    MarketDataError, PortfolioError, RateLimitError, ValidationError
)
from core.logging_config import get_logger
from core.security import CredentialManager, SecureConfig

# Initialize logger
logger = get_logger('pyportman')


# Backward compatibility classes
class one_client_class:
    """
    Backward compatible client class
    Wraps the new BrokerClient for compatibility with existing code
    """

    def __init__(
        self,
        ac_broker: str,
        ac_name: str,
        ac_id: str,
        ac_pass: str,
        ac_pin: str,
        api_key: str = '',
        totp_key: str = '',
        totp_enabled: int = 0
    ):
        """
        Initialize client (backward compatible)

        Args:
            ac_broker: Broker name (zerodha, angel)
            ac_name: Account name
            ac_id: User ID
            ac_pass: Password
            ac_pin: PIN or 2FA
            api_key: API key (for Angel)
            totp_key: TOTP key (for Zerodha)
            totp_enabled: Whether TOTP is enabled
        """
        self.ac_name = ac_name
        self.ac_id = ac_id
        self.ac_pass = ac_pass
        self.ac_pin = ac_pin
        self.ac_broker = ac_broker.lower()
        self.api_key = api_key
        self.totp_key = totp_key
        self.totp_enabled = totp_enabled

        # Initialize new client
        credentials = {
            'user_id': ac_id,
            'password': ac_pass,
            'pin': ac_pin,
            'api_key': api_key,
            'totp_key': totp_key,
            'totp_enabled': bool(totp_enabled)
        }

        self._client = ClientFactory.create_client(ac_broker, ac_name, credentials)
        self._order_manager = None
        self._portfolio_manager = None
        self._market_data_manager = None

        # Backward compatible attributes
        self.funds_equity = 0.0
        self.funds_commodity = 0.0
        self.pending_orders_list = []
        self.orders_list = []
        self.holdings_list = []
        self.positions_list = []
        self.gtt_list = []

        logger.info(f"Initialized backward compatible client for {ac_name}")

    def do_login(self):
        """Login to broker (backward compatible)"""
        try:
            success = self._client.login()
            if success:
                # Initialize managers
                self._order_manager = OrderManager(self._client)
                self._portfolio_manager = PortfolioManager(self._client)
                self._market_data_manager = MarketDataManager(self._client)

                # Update funds
                funds = self._client.check_funds()
                self.funds_equity = funds.get('equity', 0)
                self.funds_commodity = funds.get('commodity', 0)

                return self._client
        except Exception as e:
            logger.error(f"Login failed for {self.ac_name}: {e}")
            raise

    def get_orders_list(self) -> List:
        """Get all orders (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        orders = self._order_manager.get_orders()
        self.orders_list = [order_class(o.to_dict()) for o in orders]
        return self.orders_list

    def get_pending_orders(self) -> List:
        """Get pending orders (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        orders = self._order_manager.get_pending_orders()
        self.pending_orders_list = [order_class(o.to_dict()) for o in orders]
        return self.pending_orders_list

    def get_holdings_list(self) -> List:
        """Get holdings (backward compatible)"""
        if not self._portfolio_manager:
            raise AuthenticationError("Not logged in")

        holdings = self._portfolio_manager.get_holdings()
        self.holdings_list = [holding_class(h.to_dict()) for h in holdings]
        return self.holdings_list

    def get_positions_list(self) -> List:
        """Get positions (backward compatible)"""
        if not self._portfolio_manager:
            raise AuthenticationError("Not logged in")

        positions = self._portfolio_manager.get_positions()
        self.positions_list = [position_class(p.to_dict()) for p in positions]
        return self.positions_list

    def get_gtt_list(self) -> List:
        """Get GTT orders (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        if self._client.broker != 'zerodha':
            return []

        gtt_orders = self._order_manager.get_gtt_orders()
        self.gtt_list = [zerodha_gtt_status_class(g.to_dict()) for g in gtt_orders]
        return self.gtt_list

    def check_funds(self):
        """Check available funds (backward compatible)"""
        if not self._client:
            raise AuthenticationError("Not logged in")

        funds = self._client.check_funds()
        self.funds_equity = funds.get('equity', 0)
        self.funds_commodity = funds.get('commodity', 0)

    def place_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = 'CNC',
        exchange: str = 'NSE',
        validity: str = 'DAY',
        variety: Optional[str] = None,
        squareoff: Optional[float] = None,
        stoploss: Optional[float] = None,
        trailing_stoploss: Optional[float] = None,
        trailing_sell_quantity: Optional[int] = None,
        validity_date: Optional[datetime] = None
    ) -> Dict:
        """Place order (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        order = self._order_manager.place_order(
            symbol=symbol,
            quantity=quantity,
            transaction_type=transaction_type,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            product=product,
            exchange=exchange,
            validity=validity,
            variety=variety,
            squareoff=squareoff,
            stoploss=stoploss,
            trailing_stoploss=trailing_stoploss
        )

        return {'order_id': order.order_id, 'status': 'success'}

    def place_amo_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = 'CNC',
        exchange: str = 'NSE',
        validity: str = 'DAY'
    ) -> Dict:
        """Place AMO order (backward compatible)"""
        return self.place_order(
            symbol, quantity, transaction_type, order_type,
            price, trigger_price, product, exchange, validity, variety='amo'
        )

    def place_gtt_order(
        self,
        symbol: str,
        trigger_price: float,
        target_price: float,
        quantity: int,
        transaction_type: str,
        stop_loss: Optional[float] = None
    ) -> Dict:
        """Place GTT order (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        gtt = self._order_manager.place_gtt_order(
            symbol=symbol,
            trigger_price=trigger_price,
            target_price=target_price,
            quantity=quantity,
            transaction_type=transaction_type,
            stop_loss=stop_loss
        )

        return {'gtt_id': gtt.gtt_id, 'status': 'success'}

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel order (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        success = self._order_manager.cancel_order(order_id)
        return {'order_id': order_id, 'status': 'cancelled' if success else 'failed'}

    def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        trigger_price: Optional[float] = None,
        trailing_stoploss: Optional[float] = None,
        variety: Optional[str] = None
    ) -> Dict:
        """Modify order (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        success = self._order_manager.modify_order(
            order_id=order_id,
            price=price,
            quantity=quantity,
            trigger_price=trigger_price
        )

        return {'order_id': order_id, 'status': 'modified' if success else 'failed'}

    def modify_trailing_stoploss(self, order_id: str, new_trailing_sl: float) -> Dict:
        """Modify trailing stop-loss (backward compatible)"""
        return self.modify_order(order_id, trailing_stoploss=new_trailing_sl)

    def cancel_all_orders(self) -> List[Dict]:
        """Cancel all pending orders (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        pending_orders = self.get_pending_orders()
        results = []

        for order in pending_orders:
            result = self.cancel_order(order.order_id)
            results.append({
                'order_id': order.order_id,
                'symbol': order.tradingsymbol,
                'result': result
            })

        logger.info(f"Cancelled {len(results)} orders")
        return results

    def cancel_gtt(self, gtt_id: str) -> Dict:
        """Cancel GTT order (backward compatible)"""
        if not self._order_manager:
            raise AuthenticationError("Not logged in")

        success = self._order_manager.cancel_gtt_order(gtt_id)
        return {'gtt_id': gtt_id, 'status': 'cancelled' if success else 'failed'}

    def get_quote(self, symbol: str, exchange: str = 'NSE') -> Optional[Dict]:
        """Get quote (backward compatible)"""
        if not self._market_data_manager:
            raise AuthenticationError("Not logged in")

        quote = self._market_data_manager.get_quote(symbol, exchange)
        return quote.to_dict()

    def get_quotes(self, symbols_list: List[str], exchange: str = 'NSE') -> Dict[str, Dict]:
        """Get quotes for multiple symbols (backward compatible)"""
        if not self._market_data_manager:
            raise AuthenticationError("Not logged in")

        quotes = self._market_data_manager.get_quotes(symbols_list, exchange)
        return {symbol: quote.to_dict() for symbol, quote in quotes.items()}

    def get_historical_data(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        interval: str = 'day',
        exchange: str = 'NSE'
    ) -> pd.DataFrame:
        """Get historical data (backward compatible)"""
        if not self._market_data_manager:
            raise AuthenticationError("Not logged in")

        return self._market_data_manager.get_historical_data(
            symbol, from_date, to_date, interval, exchange
        )

    def get_intraday_data(
        self,
        symbol: str,
        interval: str = 'minute',
        days: int = 1,
        exchange: str = 'NSE'
    ) -> pd.DataFrame:
        """Get intraday data (backward compatible)"""
        if not self._market_data_manager:
            raise AuthenticationError("Not logged in")

        return self._market_data_manager.get_intraday_data(
            symbol, interval, days, exchange
        )

    def calculate_portfolio_pnl(self) -> Dict[str, float]:
        """Calculate portfolio P&L (backward compatible)"""
        if not self._portfolio_manager:
            raise AuthenticationError("Not logged in")

        return self._portfolio_manager.calculate_pnl()

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary (backward compatible)"""
        if not self._portfolio_manager:
            raise AuthenticationError("Not logged in")

        summary = self._portfolio_manager.get_portfolio_summary()
        return summary.to_dict()

    def get_sector_allocation(self) -> Dict[str, Dict]:
        """Get sector allocation (backward compatible)"""
        if not self._portfolio_manager:
            raise AuthenticationError("Not logged in")

        return self._portfolio_manager.get_sector_allocation()


class my_clients_group:
    """
    Backward compatible clients group
    Manages multiple broker clients
    """

    def __init__(self, user_df: pd.DataFrame):
        """
        Initialize clients group

        Args:
            user_df: DataFrame with user credentials
        """
        self.user_df = user_df
        self.user_list = []
        self._client_manager = ClientManager()

    def do_login_df(self):
        """Login all users from DataFrame (backward compatible)"""
        for index, row in self.user_df.iterrows():
            try:
                ac_name = row['ac_name']
                ac_id = row['ac_id']
                ac_pass = row['ac_pass']
                ac_pin = row['ac_pin']
                ac_broker = row['ac_broker']
                api_key = row.get('api_key', '')
                totp_key = row.get('totp_key', '')
                totp_enabled = row.get('totp_enabled', 0)

                # Create client
                client = one_client_class(
                    ac_broker, ac_name, ac_id, ac_pass, ac_pin,
                    api_key, totp_key, totp_enabled
                )

                # Login
                client.do_login()

                # Add to list
                self.user_list.append(client)

                # Also add to new client manager
                credentials = {
                    'user_id': ac_id,
                    'password': ac_pass,
                    'pin': ac_pin,
                    'api_key': api_key,
                    'totp_key': totp_key,
                    'totp_enabled': bool(totp_enabled)
                }
                self._client_manager.add_client(ac_broker, ac_name, credentials)

            except Exception as e:
                logger.error(f"Failed to login user {row.get('ac_name', 'unknown')}: {e}")

    def get_consolidated_holdings(self) -> Dict:
        """Get consolidated holdings (backward compatible)"""
        multi_manager = MultiAccountPortfolioManager(
            [client._client for client in self.user_list]
        )
        return multi_manager.get_consolidated_holdings()

    def get_consolidated_positions(self) -> Dict:
        """Get consolidated positions (backward compatible)"""
        multi_manager = MultiAccountPortfolioManager(
            [client._client for client in self.user_list]
        )
        return multi_manager.get_consolidated_positions()

    def get_total_funds(self) -> Dict:
        """Get total funds (backward compatible)"""
        multi_manager = MultiAccountPortfolioManager(
            [client._client for client in self.user_list]
        )
        return multi_manager.get_total_funds()

    def place_order_all_accounts(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = 'CNC',
        exchange: str = 'NSE',
        validity: str = 'DAY'
    ) -> Dict:
        """Place order across all accounts (backward compatible)"""
        results = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'by_account': {}
        }

        for client in self.user_list:
            try:
                result = client.place_order(
                    symbol, quantity, transaction_type, order_type,
                    price, trigger_price, product, exchange, validity
                )

                results['by_account'][client.ac_name] = {
                    'broker': client.ac_broker,
                    'result': result,
                    'status': 'success' if result.get('status') == 'success' else 'failed'
                }

                results['total_orders'] += 1
                if result.get('status') == 'success':
                    results['successful_orders'] += 1
                else:
                    results['failed_orders'] += 1

            except Exception as e:
                logger.error(f"Failed to place order for {client.ac_name}: {e}")
                results['by_account'][client.ac_name] = {
                    'broker': client.ac_broker,
                    'result': None,
                    'status': 'failed'
                }
                results['total_orders'] += 1
                results['failed_orders'] += 1

        return results

    def get_consolidated_pnl(self) -> Dict:
        """Get consolidated P&L (backward compatible)"""
        consolidated_pnl = {
            'total_pnl': 0.0,
            'holdings_pnl': 0.0,
            'positions_pnl': 0.0,
            'by_account': {},
            'by_symbol': {}
        }

        for client in self.user_list:
            try:
                pnl = client.calculate_portfolio_pnl()

                consolidated_pnl['by_account'][client.ac_name] = {
                    'broker': client.ac_broker,
                    'holdings_pnl': pnl['holdings_pnl'],
                    'positions_pnl': pnl['positions_pnl'],
                    'total_pnl': pnl['total_pnl']
                }

                consolidated_pnl['holdings_pnl'] += pnl['holdings_pnl']
                consolidated_pnl['positions_pnl'] += pnl['positions_pnl']
                consolidated_pnl['total_pnl'] += pnl['total_pnl']

            except Exception as e:
                logger.error(f"Failed to get P&L for {client.ac_name}: {e}")

        return consolidated_pnl

    def cancel_all_orders_all_accounts(self) -> Dict:
        """Cancel all orders across all accounts (backward compatible)"""
        results = {
            'total_cancelled': 0,
            'by_account': {}
        }

        for client in self.user_list:
            try:
                cancel_results = client.cancel_all_orders()

                results['by_account'][client.ac_name] = {
                    'broker': client.ac_broker,
                    'cancelled_count': len(cancel_results),
                    'results': cancel_results
                }

                results['total_cancelled'] += len(cancel_results)

            except Exception as e:
                logger.error(f"Failed to cancel orders for {client.ac_name}: {e}")

        return results

    def get_consolidated_portfolio_summary(self) -> Dict:
        """Get consolidated portfolio summary (backward compatible)"""
        multi_manager = MultiAccountPortfolioManager(
            [client._client for client in self.user_list]
        )
        return multi_manager.get_consolidated_summary()


# Backward compatible data classes
class order_class:
    """Backward compatible order class"""

    def __init__(self, order_data: Dict):
        self.order_id = order_data.get('order_id', '')
        self.tradingsymbol = order_data.get('symbol', '')
        self.exchange = order_data.get('exchange', 'NSE')
        self.transaction_type = order_data.get('transaction_type', '')
        self.order_type = order_data.get('order_type', '')
        self.quantity = order_data.get('quantity', 0)
        self.price = order_data.get('price')
        self.trigger_price = order_data.get('trigger_price')
        self.product = order_data.get('product', 'CNC')
        self.status = order_data.get('status', 'UNKNOWN')
        self.average_price = order_data.get('average_price')
        self.filled_quantity = order_data.get('filled_quantity', 0)
        self.pending_quantity = order_data.get('pending_quantity', 0)
        self.validity = order_data.get('validity', 'DAY')
        self.variety = order_data.get('variety')


class holding_class:
    """Backward compatible holding class"""

    def __init__(self, holding_data: Dict):
        self.tradingsymbol = holding_data.get('symbol', '')
        self.exchange = holding_data.get('exchange', 'NSE')
        self.quantity = holding_data.get('quantity', 0)
        self.average_price = holding_data.get('average_price', 0)
        self.ltp = holding_data.get('ltp', 0)
        self.pnl = holding_data.get('pnl', 0)
        self.day_change = holding_data.get('day_change', 0)
        self.day_change_percent = holding_data.get('day_change_percent', 0)
        self.product = holding_data.get('product', 'CNC')


class position_class:
    """Backward compatible position class"""

    def __init__(self, position_data: Dict):
        self.tradingsymbol = position_data.get('symbol', '')
        self.exchange = position_data.get('exchange', 'NSE')
        self.quantity = position_data.get('quantity', 0)
        self.buy_price = position_data.get('buy_price', 0)
        self.sell_price = position_data.get('sell_price', 0)
        self.ltp = position_data.get('ltp', 0)
        self.pnl = position_data.get('pnl', 0)
        self.value = position_data.get('value', 0)
        self.product = position_data.get('product', 'MIS')
        self.position_type = position_data.get('position_type', 'LONG')


class zerodha_gtt_status_class:
    """Backward compatible GTT status class"""

    def __init__(self, gtt_data: Dict):
        self.id = gtt_data.get('gtt_id', '')
        self.tradingsymbol = gtt_data.get('symbol', '')
        self.exchange = gtt_data.get('exchange', 'NSE')
        self.trigger = gtt_data.get('trigger_price', 0)
        self.status = gtt_data.get('status', 'ACTIVE')
        self.created_at = gtt_data.get('created_at', '')


class stock_status:
    """Stock status class for trading strategies"""

    def __init__(self, one_stock_data: Dict):
        self.symbol = one_stock_data.get('symbol', '')
        self.percent = one_stock_data.get('percent', 0)
        self.buy_price = one_stock_data.get('buy', 0)
        self.sl_price = one_stock_data.get('sl', 0)
        self.target_price = one_stock_data.get('target', 0)
        self.entry_open = one_stock_data.get('entry_open', False)
        self.required_qty = 0
        self.available_qty = 0
        self.holding_qty = 0
        self.position_qty = 0


# Export main classes
__all__ = [
    # New architecture
    'BrokerClient', 'ZerodhaClient', 'AngelClient',
    'ClientFactory', 'ClientManager',
    'OrderManager', 'Order', 'GTTOrder',
    'PortfolioManager', 'MultiAccountPortfolioManager',
    'MarketDataManager', 'MarketDataUtils',
    'CredentialManager', 'SecureConfig',
    # Backward compatible
    'one_client_class', 'my_clients_group',
    'order_class', 'holding_class', 'position_class',
    'zerodha_gtt_status_class', 'stock_status',
    # Exceptions
    'PyPortManError', 'AuthenticationError', 'OrderError',
    'MarketDataError', 'PortfolioError', 'RateLimitError', 'ValidationError'
]
