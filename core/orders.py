"""
Order Management Module
Handles order placement, modification, cancellation, and GTT orders
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .error_handler import (
    OrderError, ValidationError, AuthenticationError,
    retry_on_failure, with_error_handling, RateLimiter
)
from .logging_config import get_logger
from .client import BrokerClient

logger = get_logger('pyportman.orders')


# Enums for order types
class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"


class TransactionType(Enum):
    """Transaction type enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class ProductType(Enum):
    """Product type enumeration"""
    CNC = "CNC"  # Cash and Carry
    MIS = "MIS"  # Margin Intraday Squareoff
    NRML = "NRML"  # Normal
    BO = "BO"  # Bracket Order
    CO = "CO"  # Cover Order


class Exchange(Enum):
    """Exchange enumeration"""
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NFO = "NFO"


class OrderValidity(Enum):
    """Order validity enumeration"""
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    GTD = "GTD"  # Good Till Date


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    TRIGGER_PENDING = "TRIGGER PENDING"


# Data classes
@dataclass
class Order:
    """Order data class"""
    order_id: str
    symbol: str
    exchange: str
    transaction_type: str
    order_type: str
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    product: str = "CNC"
    status: str = "PENDING"
    average_price: Optional[float] = None
    filled_quantity: int = 0
    pending_quantity: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    validity: str = "DAY"
    variety: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'transaction_type': self.transaction_type,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'product': self.product,
            'status': self.status,
            'average_price': self.average_price,
            'filled_quantity': self.filled_quantity,
            'pending_quantity': self.pending_quantity,
            'timestamp': self.timestamp.isoformat(),
            'validity': self.validity,
            'variety': self.variety
        }


@dataclass
class GTTOrder:
    """GTT (Good Till Triggered) order data class"""
    gtt_id: str
    symbol: str
    exchange: str
    trigger_price: float
    target_price: float
    quantity: int
    transaction_type: str
    stop_loss: Optional[float] = None
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert GTT order to dictionary"""
        return {
            'gtt_id': self.gtt_id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'trigger_price': self.trigger_price,
            'target_price': self.target_price,
            'quantity': self.quantity,
            'transaction_type': self.transaction_type,
            'stop_loss': self.stop_loss,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None
        }


# Order Manager
class OrderManager:
    """
    Manages order operations for a broker client
    """

    def __init__(self, client: BrokerClient):
        """
        Initialize order manager

        Args:
            client: Broker client instance
        """
        self.client = client
        self.rate_limiter = RateLimiter(max_calls=20, period=60)

    def _validate_order_params(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = "CNC",
        exchange: str = "NSE",
        validity: str = "DAY"
    ) -> None:
        """
        Validate order parameters

        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate symbol
        if not symbol or not isinstance(symbol, str):
            raise ValidationError("Symbol must be a non-empty string")
        symbol = symbol.strip().upper()

        # Validate quantity
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError("Quantity must be a positive integer")

        # Validate transaction type
        transaction_type = transaction_type.strip().upper()
        if transaction_type not in [t.value for t in TransactionType]:
            raise ValidationError(f"Transaction type must be one of: {[t.value for t in TransactionType]}")

        # Validate order type
        order_type = order_type.strip().upper()
        if order_type not in [t.value for t in OrderType]:
            raise ValidationError(f"Order type must be one of: {[t.value for t in OrderType]}")

        # Validate price for LIMIT orders
        if order_type == OrderType.LIMIT.value and (price is None or price <= 0):
            raise ValidationError("Price is required for LIMIT orders")

        # Validate trigger price for SL orders
        if order_type in [OrderType.STOP_LOSS.value, OrderType.STOP_LOSS_MARKET.value]:
            if trigger_price is None or trigger_price <= 0:
                raise ValidationError("Trigger price is required for SL orders")

        # Validate product
        product = product.strip().upper()
        if product not in [p.value for p in ProductType]:
            raise ValidationError(f"Product must be one of: {[p.value for p in ProductType]}")

        # Validate exchange
        exchange = exchange.strip().upper()
        if exchange not in [e.value for e in Exchange]:
            raise ValidationError(f"Exchange must be one of: {[e.value for e in Exchange]}")

        # Validate validity
        validity = validity.strip().upper()
        if validity not in [v.value for v in OrderValidity]:
            raise ValidationError(f"Validity must be one of: {[v.value for v in OrderValidity]}")

    @retry_on_failure(max_retries=3, exceptions=(Exception,))
    @with_error_handling(logger=logger, raise_on_error=True)
    def place_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = "CNC",
        exchange: str = "NSE",
        validity: str = "DAY",
        variety: Optional[str] = None,
        squareoff: Optional[float] = None,
        stoploss: Optional[float] = None,
        trailing_stoploss: Optional[float] = None
    ) -> Order:
        """
        Place an order

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            transaction_type: BUY or SELL
            order_type: MARKET, LIMIT, SL, SL-M
            price: Limit price (required for LIMIT orders)
            trigger_price: Trigger price (required for SL orders)
            product: Product type (CNC, MIS, NRML, BO, CO)
            exchange: Exchange (NSE, BSE, MCX, NFO)
            validity: Order validity (DAY, IOC, GTD)
            variety: Order variety (regular, amo, bo, co)
            squareoff: Squareoff points for BO orders
            stoploss: Stoploss points for BO/CO orders
            trailing_stoploss: Trailing stoploss for BO orders

        Returns:
            Order object

        Raises:
            ValidationError: If parameters are invalid
            OrderError: If order placement fails
        """
        # Validate parameters
        self._validate_order_params(
            symbol, quantity, transaction_type, order_type,
            price, trigger_price, product, exchange, validity
        )

        # Check rate limit
        self.rate_limiter.wait_if_needed(logger=logger)

        # Ensure client is authenticated
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        # Place order based on broker
        if self.client.broker == 'zerodha':
            return self._place_order_zerodha(
                symbol, quantity, transaction_type, order_type,
                price, trigger_price, product, exchange, validity,
                variety, squareoff, stoploss, trailing_stoploss
            )
        elif self.client.broker == 'angel':
            return self._place_order_angel(
                symbol, quantity, transaction_type, order_type,
                price, trigger_price, product, exchange, validity,
                variety, squareoff, stoploss, trailing_stoploss
            )
        else:
            raise OrderError(f"Order placement not implemented for broker: {self.client.broker}")

    def _place_order_zerodha(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        price: Optional[float],
        trigger_price: Optional[float],
        product: str,
        exchange: str,
        validity: str,
        variety: Optional[str],
        squareoff: Optional[float],
        stoploss: Optional[float],
        trailing_stoploss: Optional[float]
    ) -> Order:
        """Place order for Zerodha"""
        try:
            api = self.client.api

            order_params = {
                'tradingsymbol': symbol,
                'exchange': exchange,
                'quantity': quantity,
                'transaction_type': transaction_type,
                'order_type': order_type,
                'product': product,
                'validity': validity
            }

            if variety:
                order_params['variety'] = variety

            if order_type in ['LIMIT', 'SL'] and price is not None:
                order_params['price'] = price

            if order_type in ['SL', 'SL-M'] and trigger_price is not None:
                order_params['trigger_price'] = trigger_price

            if squareoff is not None:
                order_params['squareoff'] = squareoff
            if stoploss is not None:
                order_params['stoploss'] = stoploss
            if trailing_stoploss is not None:
                order_params['trailing_stoploss'] = trailing_stoploss

            order_id = api.place_order(order_params)

            logger.info(f"Zerodha order placed: {order_id} for {symbol}")

            return Order(
                order_id=order_id,
                symbol=symbol,
                exchange=exchange,
                transaction_type=transaction_type,
                order_type=order_type,
                quantity=quantity,
                price=price,
                trigger_price=trigger_price,
                product=product,
                status="PENDING",
                validity=validity,
                variety=variety
            )

        except Exception as e:
            raise OrderError(f"Zerodha order placement failed: {str(e)}")

    def _place_order_angel(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        price: Optional[float],
        trigger_price: Optional[float],
        product: str,
        exchange: str,
        validity: str,
        variety: Optional[str],
        squareoff: Optional[float],
        stoploss: Optional[float],
        trailing_stoploss: Optional[float]
    ) -> Order:
        """Place order for Angel Broking"""
        try:
            api = self.client.api

            # Get instrument token
            instrument_token = self._get_angel_instrument_token(symbol, exchange)

            # Map variety
            variety_map = {
                'regular': 'NORMAL',
                'amo': 'AMO',
                'bo': 'BO',
                'co': 'CO'
            }
            angel_variety = variety_map.get(variety, 'NORMAL')

            order_params = {
                'variety': angel_variety,
                'tradingsymbol': symbol,
                'symboltoken': instrument_token,
                'transactiontype': transaction_type,
                'exchange': exchange,
                'ordertype': order_type,
                'producttype': product,
                'duration': validity,
                'price': price if price else 0,
                'squareoff': str(squareoff) if squareoff is not None else '0',
                'stoploss': str(stoploss) if stoploss is not None else '0',
                'quantity': quantity
            }

            if trigger_price:
                order_params['triggerprice'] = trigger_price

            if trailing_stoploss is not None:
                order_params['trailingstoploss'] = str(trailing_stoploss)

            order_id = api.placeOrder(order_params)

            logger.info(f"Angel order placed: {order_id} for {symbol}")

            return Order(
                order_id=order_id,
                symbol=symbol,
                exchange=exchange,
                transaction_type=transaction_type,
                order_type=order_type,
                quantity=quantity,
                price=price,
                trigger_price=trigger_price,
                product=product,
                status="PENDING",
                validity=validity,
                variety=variety
            )

        except Exception as e:
            raise OrderError(f"Angel order placement failed: {str(e)}")

    def _get_angel_instrument_token(self, symbol: str, exchange: str) -> str:
        """Get instrument token for Angel"""
        try:
            api = self.client.api
            search_params = {
                'exchange': exchange,
                'searchtext': symbol
            }
            result = api.searchscrip(search_params)
            if result and 'data' in result and len(result['data']) > 0:
                return result['data'][0]['symboltoken']
        except Exception as e:
            logger.error(f"Error getting Angel instrument token: {e}")
        raise OrderError(f"Could not find instrument token for {symbol}")

    @retry_on_failure(max_retries=2, exceptions=(Exception,))
    @with_error_handling(logger=logger, raise_on_error=True)
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful

        Raises:
            OrderError: If cancellation fails
        """
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            if self.client.broker == 'zerodha':
                self.client.api.cancel_order(order_id)
            elif self.client.broker == 'angel':
                self.client.api.cancelOrder(order_id)
            else:
                raise OrderError(f"Cancel not implemented for broker: {self.client.broker}")

            logger.info(f"Order cancelled: {order_id}")
            return True

        except Exception as e:
            raise OrderError(f"Order cancellation failed: {str(e)}")

    @retry_on_failure(max_retries=2, exceptions=(Exception,))
    @with_error_handling(logger=logger, raise_on_error=True)
    def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        trigger_price: Optional[float] = None
    ) -> bool:
        """
        Modify an existing order

        Args:
            order_id: Order ID to modify
            price: New price
            quantity: New quantity
            trigger_price: New trigger price

        Returns:
            True if modification successful

        Raises:
            OrderError: If modification fails
        """
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            if self.client.broker == 'zerodha':
                modify_params = {'order_id': order_id}
                if price is not None:
                    modify_params['price'] = price
                if quantity is not None:
                    modify_params['quantity'] = quantity
                if trigger_price is not None:
                    modify_params['trigger_price'] = trigger_price

                self.client.api.modify_order(order_id, modify_params)

            elif self.client.broker == 'angel':
                modify_params = {
                    'variety': 'NORMAL',
                    'orderid': order_id
                }
                if price is not None:
                    modify_params['price'] = price
                if quantity is not None:
                    modify_params['quantity'] = quantity
                if trigger_price is not None:
                    modify_params['triggerprice'] = trigger_price

                self.client.api.modifyOrder(modify_params)

            else:
                raise OrderError(f"Modify not implemented for broker: {self.client.broker}")

            logger.info(f"Order modified: {order_id}")
            return True

        except Exception as e:
            raise OrderError(f"Order modification failed: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_orders(self) -> List[Order]:
        """
        Get all orders for the account

        Returns:
            List of Order objects

        Raises:
            OrderError: If fetching orders fails
        """
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            if self.client.broker == 'zerodha':
                orders_data = self.client.api.orders()
            elif self.client.broker == 'angel':
                orders_data = self.client.api.orderBook()['data']
            else:
                raise OrderError(f"Get orders not implemented for broker: {self.client.broker}")

            orders = []
            for order_data in orders_data:
                orders.append(self._parse_order(order_data))

            return orders

        except Exception as e:
            raise OrderError(f"Failed to get orders: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_pending_orders(self) -> List[Order]:
        """
        Get pending orders

        Returns:
            List of pending Order objects

        Raises:
            OrderError: If fetching orders fails
        """
        all_orders = self.get_orders()
        return [order for order in all_orders if order.status in ["OPEN", "open", "PENDING"]]

    def _parse_order(self, order_data: Dict[str, Any]) -> Order:
        """Parse order data from broker API"""
        # This is a simplified parser - actual implementation depends on broker response format
        return Order(
            order_id=order_data.get('order_id', order_data.get('orderid', '')),
            symbol=order_data.get('tradingsymbol', order_data.get('symbol', '')),
            exchange=order_data.get('exchange', 'NSE'),
            transaction_type=order_data.get('transaction_type', order_data.get('transactiontype', '')),
            order_type=order_data.get('order_type', order_data.get('ordertype', '')),
            quantity=order_data.get('quantity', 0),
            price=order_data.get('price'),
            trigger_price=order_data.get('trigger_price', order_data.get('triggerprice')),
            product=order_data.get('product', order_data.get('producttype', 'CNC')),
            status=order_data.get('status', 'UNKNOWN'),
            average_price=order_data.get('average_price'),
            filled_quantity=order_data.get('filled_quantity', 0),
            pending_quantity=order_data.get('pending_quantity', 0),
            validity=order_data.get('validity', order_data.get('duration', 'DAY'))
        )

    # GTT Order Methods (Zerodha only)
    @with_error_handling(logger=logger, raise_on_error=True)
    def place_gtt_order(
        self,
        symbol: str,
        trigger_price: float,
        target_price: float,
        quantity: int,
        transaction_type: str,
        stop_loss: Optional[float] = None
    ) -> GTTOrder:
        """
        Place a GTT (Good Till Triggered) order (Zerodha only)

        Args:
            symbol: Trading symbol
            trigger_price: Price to trigger the order
            target_price: Target price for the order
            quantity: Order quantity
            transaction_type: BUY or SELL
            stop_loss: Optional stop-loss price

        Returns:
            GTTOrder object

        Raises:
            OrderError: If GTT placement fails
        """
        if self.client.broker != 'zerodha':
            raise OrderError("GTT orders are only supported for Zerodha")

        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            gtt_params = {
                'tradingsymbol': symbol,
                'exchange': 'NSE',
                'trigger_values': [trigger_price],
                'last_price': trigger_price,
                'orders': [{
                    'exchange': 'NSE',
                    'tradingsymbol': symbol,
                    'transaction_type': transaction_type,
                    'quantity': quantity,
                    'order_type': 'LIMIT',
                    'product': 'CNC',
                    'price': target_price
                }]
            }

            gtt_id = self.client.api.place_gtt(gtt_params)

            logger.info(f"GTT order placed: {gtt_id} for {symbol}")

            return GTTOrder(
                gtt_id=gtt_id,
                symbol=symbol,
                exchange='NSE',
                trigger_price=trigger_price,
                target_price=target_price,
                quantity=quantity,
                transaction_type=transaction_type,
                stop_loss=stop_loss,
                status="ACTIVE"
            )

        except Exception as e:
            raise OrderError(f"GTT order placement failed: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def cancel_gtt_order(self, gtt_id: str) -> bool:
        """
        Cancel a GTT order (Zerodha only)

        Args:
            gtt_id: GTT order ID to cancel

        Returns:
            True if cancellation successful

        Raises:
            OrderError: If cancellation fails
        """
        if self.client.broker != 'zerodha':
            raise OrderError("GTT orders are only supported for Zerodha")

        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            self.client.api.delete_gtt(gtt_id)
            logger.info(f"GTT order cancelled: {gtt_id}")
            return True

        except Exception as e:
            raise OrderError(f"GTT cancellation failed: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_gtt_orders(self) -> List[GTTOrder]:
        """
        Get all GTT orders (Zerodha only)

        Returns:
            List of GTTOrder objects

        Raises:
            OrderError: If fetching GTT orders fails
        """
        if self.client.broker != 'zerodha':
            raise OrderError("GTT orders are only supported for Zerodha")

        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            gtt_data = self.client.api.get_gtts()

            gtt_orders = []
            for gtt in gtt_data:
                gtt_orders.append(self._parse_gtt_order(gtt))

            return gtt_orders

        except Exception as e:
            raise OrderError(f"Failed to get GTT orders: {str(e)}")

    def _parse_gtt_order(self, gtt_data: Dict[str, Any]) -> GTTOrder:
        """Parse GTT order data from Zerodha API"""
        return GTTOrder(
            gtt_id=gtt_data.get('id', ''),
            symbol=gtt_data.get('tradingsymbol', ''),
            exchange=gtt_data.get('exchange', 'NSE'),
            trigger_price=gtt_data.get('trigger', {}).get('values', [0])[0],
            target_price=gtt_data.get('orders', [{}])[0].get('price', 0),
            quantity=gtt_data.get('orders', [{}])[0].get('quantity', 0),
            transaction_type=gtt_data.get('orders', [{}])[0].get('transaction_type', ''),
            status=gtt_data.get('status', 'ACTIVE'),
            created_at=datetime.fromisoformat(gtt_data.get('created_at', datetime.now().isoformat()))
        )
