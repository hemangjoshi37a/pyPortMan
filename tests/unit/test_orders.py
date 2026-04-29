"""Unit tests for orders module"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from core.orders import (
    OrderType,
    TransactionType,
    ProductType,
    Exchange,
    OrderValidity,
    OrderStatus,
    Order,
    GTTOrder,
    OrderManager
)


class TestEnums:
    """Test order-related enums"""

    def test_order_type_values(self):
        """Test OrderType enum values"""
        assert OrderType.MARKET.value == 'MARKET'
        assert OrderType.LIMIT.value == 'LIMIT'
        assert OrderType.STOP_LOSS.value == 'SL'
        assert OrderType.STOP_LOSS_MARKET.value == 'SL-M'

    def test_transaction_type_values(self):
        """Test TransactionType enum values"""
        assert TransactionType.BUY.value == 'BUY'
        assert TransactionType.SELL.value == 'SELL'

    def test_product_type_values(self):
        """Test ProductType enum values"""
        assert ProductType.CNC.value == 'CNC'
        assert ProductType.MIS.value == 'MIS'
        assert ProductType.NRML.value == 'NRML'
        assert ProductType.BO.value == 'BO'
        assert ProductType.CO.value == 'CO'

    def test_exchange_values(self):
        """Test Exchange enum values"""
        assert Exchange.NSE.value == 'NSE'
        assert Exchange.BSE.value == 'BSE'
        assert Exchange.MCX.value == 'MCX'
        assert Exchange.NFO.value == 'NFO'

    def test_order_validity_values(self):
        """Test OrderValidity enum values"""
        assert OrderValidity.DAY.value == 'DAY'
        assert OrderValidity.IOC.value == 'IOC'
        assert OrderValidity.GTD.value == 'GTD'

    def test_order_status_values(self):
        """Test OrderStatus enum values"""
        assert OrderStatus.PENDING.value == 'OPEN'
        assert OrderStatus.COMPLETE.value == 'COMPLETE'
        assert OrderStatus.CANCELLED.value == 'CANCELLED'
        assert OrderStatus.REJECTED.value == 'REJECTED'
        assert OrderStatus.TRIGGER_PENDING.value == 'TRIGGER_PENDING'


class TestOrder:
    """Test Order dataclass"""

    def test_order_creation(self):
        """Test creating an Order"""
        order = Order(
            order_id='ORD123456',
            symbol='RELIANCE',
            exchange='NSE',
            transaction_type=TransactionType.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=2500.0,
            trigger_price=None,
            product=ProductType.CNC,
            status=OrderStatus.PENDING,
            average_price=0.0,
            filled_quantity=0,
            pending_quantity=10,
            timestamp=datetime.now(),
            validity=OrderValidity.DAY,
            variety='REGULAR'
        )

        assert order.order_id == 'ORD123456'
        assert order.symbol == 'RELIANCE'
        assert order.quantity == 10

    def test_order_to_dict(self):
        """Test converting Order to dict"""
        order = Order(
            order_id='ORD123456',
            symbol='RELIANCE',
            exchange='NSE',
            transaction_type=TransactionType.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=2500.0,
            trigger_price=None,
            product=ProductType.CNC,
            status=OrderStatus.PENDING,
            average_price=0.0,
            filled_quantity=0,
            pending_quantity=10,
            timestamp=datetime.now(),
            validity=OrderValidity.DAY,
            variety='REGULAR'
        )

        result = order.to_dict()
        assert isinstance(result, dict)
        assert result['order_id'] == 'ORD123456'
        assert result['symbol'] == 'RELIANCE'


class TestGTTOrder:
    """Test GTTOrder dataclass"""

    def test_gtt_order_creation(self):
        """Test creating a GTTOrder"""
        gtt_order = GTTOrder(
            gtt_id='GTT123456',
            symbol='RELIANCE',
            exchange='NSE',
            trigger_price=2550.0,
            target_price=2600.0,
            quantity=10,
            transaction_type=TransactionType.BUY,
            stop_loss=2450.0,
            status='ACTIVE',
            created_at=datetime.now(),
            triggered_at=None
        )

        assert gtt_order.gtt_id == 'GTT123456'
        assert gtt_order.trigger_price == 2550.0
        assert gtt_order.target_price == 2600.0

    def test_gtt_order_to_dict(self):
        """Test converting GTTOrder to dict"""
        gtt_order = GTTOrder(
            gtt_id='GTT123456',
            symbol='RELIANCE',
            exchange='NSE',
            trigger_price=2550.0,
            target_price=2600.0,
            quantity=10,
            transaction_type=TransactionType.BUY,
            stop_loss=2450.0,
            status='ACTIVE',
            created_at=datetime.now(),
            triggered_at=None
        )

        result = gtt_order.to_dict()
        assert isinstance(result, dict)
        assert result['gtt_id'] == 'GTT123456'
        assert result['symbol'] == 'RELIANCE'


class TestOrderManager:
    """Test OrderManager class"""

    @pytest.fixture
    def mock_client(self):
        """Mock broker client"""
        client = Mock()
        client.broker = 'zerodha'
        client.account_name = 'test_account'
        client._authenticated = True
        return client

    @pytest.fixture
    def order_manager(self, mock_client):
        """Create OrderManager instance"""
        return OrderManager(mock_client)

    def test_initialization(self, order_manager):
        """Test OrderManager initialization"""
        assert order_manager.client is not None
        assert order_manager._rate_limiter is not None

    def test_place_order_zerodha(self, order_manager):
        """Test placing order with Zerodha"""
        order_manager.client.api = Mock()
        order_manager.client.api.place_order.return_value = {
            'order_id': 'ORD123456',
            'status': 'OPEN'
        }

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
        assert order.status == OrderStatus.PENDING

    def test_place_order_angel(self, order_manager):
        """Test placing order with Angel"""
        order_manager.client.broker = 'angel'
        order_manager.client.api = Mock()
        order_manager.client.api.order.return_value = {
            'orderid': 'ORD123456',
            'status': 'open'
        }

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

    def test_cancel_order(self, order_manager):
        """Test cancelling an order"""
        order_manager.client.api = Mock()
        order_manager.client.api.cancel_order.return_value = {
            'order_id': 'ORD123456',
            'status': 'CANCELLED'
        }

        result = order_manager.cancel_order('ORD123456')
        assert result is True

    def test_modify_order(self, order_manager):
        """Test modifying an order"""
        order_manager.client.api = Mock()
        order_manager.client.api.modify_order.return_value = {
            'order_id': 'ORD123456',
            'status': 'OPEN',
            'price': 2550.0,
            'quantity': 15
        }

        order = order_manager.modify_order(
            order_id='ORD123456',
            price=2550.0,
            quantity=15
        )

        assert order.price == 2550.0
        assert order.quantity == 15

    def test_get_orders(self, order_manager):
        """Test getting all orders"""
        order_manager.client.api = Mock()
        order_manager.client.api.orders.return_value = [
            {'order_id': 'ORD123456', 'status': 'OPEN', 'tradingsymbol': 'RELIANCE'},
            {'order_id': 'ORD123457', 'status': 'COMPLETE', 'tradingsymbol': 'TCS'}
        ]

        orders = order_manager.get_orders()

        assert len(orders) == 2
        assert orders[0].order_id == 'ORD123456'

    def test_get_pending_orders(self, order_manager):
        """Test getting pending orders"""
        order_manager.client.api = Mock()
        order_manager.client.api.orders.return_value = [
            {'order_id': 'ORD123456', 'status': 'OPEN', 'tradingsymbol': 'RELIANCE'},
            {'order_id': 'ORD123457', 'status': 'COMPLETE', 'tradingsymbol': 'TCS'}
        ]

        pending_orders = order_manager.get_pending_orders()

        assert len(pending_orders) == 1
        assert pending_orders[0].order_id == 'ORD123456'

    def test_place_gtt_order(self, order_manager):
        """Test placing GTT order"""
        order_manager.client.api = Mock()
        order_manager.client.api.place_gtt.return_value = {
            'id': 'GTT123456',
            'status': 'ACTIVE'
        }

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

    def test_cancel_gtt_order(self, order_manager):
        """Test cancelling GTT order"""
        order_manager.client.api = Mock()
        order_manager.client.api.delete_gtt.return_value = {
            'id': 'GTT123456',
            'status': 'CANCELLED'
        }

        result = order_manager.cancel_gtt_order('GTT123456')
        assert result is True

    def test_get_gtt_orders(self, order_manager):
        """Test getting GTT orders"""
        order_manager.client.api = Mock()
        order_manager.client.api.get_gtts.return_value = [
            {'id': 'GTT123456', 'status': 'ACTIVE', 'tradingsymbol': 'RELIANCE'},
            {'id': 'GTT123457', 'status': 'TRIGGERED', 'tradingsymbol': 'TCS'}
        ]

        gtt_orders = order_manager.get_gtt_orders()

        assert len(gtt_orders) == 2
        assert gtt_orders[0].gtt_id == 'GTT123456'

    def test_validate_order_params_valid(self, order_manager):
        """Test validating order params - valid"""
        # Should not raise any exception
        order_manager._validate_order_params(
            symbol='RELIANCE',
            exchange='NSE',
            transaction_type=TransactionType.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=2500.0,
            product=ProductType.CNC
        )

    def test_validate_order_params_invalid_quantity(self, order_manager):
        """Test validating order params - invalid quantity"""
        with pytest.raises(Exception):
            order_manager._validate_order_params(
                symbol='RELIANCE',
                exchange='NSE',
                transaction_type=TransactionType.BUY,
                order_type=OrderType.LIMIT,
                quantity=0,
                price=2500.0,
                product=ProductType.CNC
            )

    def test_validate_order_params_invalid_price(self, order_manager):
        """Test validating order params - invalid price"""
        with pytest.raises(Exception):
            order_manager._validate_order_params(
                symbol='RELIANCE',
                exchange='NSE',
                transaction_type=TransactionType.BUY,
                order_type=OrderType.LIMIT,
                quantity=10,
                price=0.0,
                product=ProductType.CNC
            )
