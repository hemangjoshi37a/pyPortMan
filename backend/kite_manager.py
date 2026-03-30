"""
KiteConnect Multi-Account Manager for pyPortMan
Handles multiple Zerodha accounts with KiteConnect API
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from kiteconnect import KiteConnect
from sqlalchemy.orm import Session

from models import Account, Holding, Order, Position, PortfolioSnapshot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class KiteManager:
    """Manager for multiple Zerodha KiteConnect accounts"""

    def __init__(self, db: Session):
        self.db = db
        self._kite_instances: Dict[int, KiteConnect] = {}

    def get_all_accounts(self) -> List[Account]:
        """Get all active accounts from database"""
        return self.db.query(Account).filter(Account.is_active == True).all()

    def get_account(self, account_id: int) -> Optional[Account]:
        """Get a specific account by ID"""
        return self.db.query(Account).filter(Account.id == account_id).first()

    def get_kite(self, account_id: int) -> Optional[KiteConnect]:
        """
        Get or create KiteConnect instance for an account
        Returns None if account not found or token expired
        """
        account = self.get_account(account_id)
        if not account:
            logger.error(f"Account {account_id} not found")
            return None

        # Check if token is expired (tokens expire daily at 6 AM IST)
        if account.token_expires_at and datetime.utcnow() > account.token_expires_at:
            logger.warning(f"Access token expired for account {account_id}")
            return None

        # Return cached instance if available
        if account_id in self._kite_instances:
            return self._kite_instances[account_id]

        # Create new KiteConnect instance
        try:
            kite = KiteConnect(api_key=account.api_key)
            kite.set_access_token(account.access_token)
            self._kite_instances[account_id] = kite
            logger.info(f"KiteConnect instance created for account {account_id}")
            return kite
        except Exception as e:
            logger.error(f"Error creating KiteConnect instance: {e}")
            return None

    def generate_login_url(self, account_id: int) -> Optional[str]:
        """
        Generate Zerodha login URL for obtaining request token
        """
        account = self.get_account(account_id)
        if not account:
            logger.error(f"Account {account_id} not found")
            return None

        try:
            kite = KiteConnect(api_key=account.api_key)
            return kite.login_url()
        except Exception as e:
            logger.error(f"Error generating login URL: {e}")
            return None

    def generate_session(self, account_id: int, request_token: str) -> bool:
        """
        Generate access token from request token after user login
        Returns True if successful
        """
        account = self.get_account(account_id)
        if not account:
            logger.error(f"Account {account_id} not found")
            return False

        try:
            kite = KiteConnect(api_key=account.api_key)
            data = kite.generate_session(request_token, account.api_secret)

            # Update account with new access token
            account.access_token = data["access_token"]
            account.request_token = request_token
            account.last_login_at = datetime.utcnow()
            # Token expires at 6 AM IST next day
            account.token_expires_at = datetime.utcnow().replace(hour=0, minute=30) + timedelta(days=1)

            self.db.commit()

            # Clear cached instance
            if account_id in self._kite_instances:
                del self._kite_instances[account_id]

            logger.info(f"Session generated successfully for account {account_id}")
            return True
        except Exception as e:
            logger.error(f"Error generating session: {e}")
            self.db.rollback()
            return False

    def fetch_holdings(self, account_id: int) -> List[Holding]:
        """
        Fetch holdings from Zerodha and update database
        Returns list of holdings
        """
        kite = self.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            holdings_data = kite.holdings()

            # Delete old holdings for this account
            self.db.query(Holding).filter(Holding.account_id == account_id).delete()

            # Insert new holdings
            holdings = []
            for item in holdings_data:
                qty = item.get("quantity", 0)
                avg_price = item.get("average_price", 0)
                ltp = item.get("last_price", 0)
                current_value = qty * ltp
                investment_value = qty * avg_price
                pnl = current_value - investment_value
                pnl_percent = (pnl / investment_value * 100) if investment_value > 0 else 0

                holding = Holding(
                    account_id=account_id,
                    stock=item.get("tradingsymbol", ""),
                    exchange=item.get("exchange", "NSE"),
                    qty=qty,
                    avg_price=avg_price,
                    ltp=ltp,
                    current_value=current_value,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    product=item.get("product", "CNC"),
                    isin=item.get("isin", ""),
                    updated_at=datetime.utcnow()
                )
                self.db.add(holding)
                holdings.append(holding)

            self.db.commit()
            logger.info(f"Fetched {len(holdings)} holdings for account {account_id}")
            return holdings

        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            self.db.rollback()
            # Return cached holdings from database
            return self.db.query(Holding).filter(Holding.account_id == account_id).all()

    def fetch_positions(self, account_id: int) -> List[Position]:
        """
        Fetch intraday positions from Zerodha and update database
        Returns list of positions
        """
        kite = self.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            positions_data = kite.positions()

            # Delete old positions for this account
            self.db.query(Position).filter(Position.account_id == account_id).delete()

            # Insert new positions (only net positions)
            positions = []
            net_positions = positions_data.get("net", [])

            for item in net_positions:
                qty = item.get("quantity", 0)
                if qty == 0:
                    continue  # Skip closed positions

                avg_price = item.get("average_price", 0)
                ltp = item.get("last_price", 0)
                pnl = item.get("pnl", 0)
                pnl_percent = item.get("pnl_percentage", 0)

                position = Position(
                    account_id=account_id,
                    stock=item.get("tradingsymbol", ""),
                    exchange=item.get("exchange", "NSE"),
                    qty=qty,
                    avg_price=avg_price,
                    ltp=ltp,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    product=item.get("product", "MIS"),
                    product_type="intraday",
                    buy_qty=item.get("buy_quantity", 0),
                    sell_qty=item.get("sell_quantity", 0),
                    buy_avg_price=item.get("buy_price", 0),
                    sell_avg_price=item.get("sell_price", 0),
                    unrealized_pnl=item.get("unrealised_pnl", 0),
                    realized_pnl=item.get("realised_pnl", 0),
                    updated_at=datetime.utcnow()
                )
                self.db.add(position)
                positions.append(position)

            self.db.commit()
            logger.info(f"Fetched {len(positions)} positions for account {account_id}")
            return positions

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            self.db.rollback()
            return self.db.query(Position).filter(Position.account_id == account_id).all()

    def fetch_orders(self, account_id: int) -> List[Order]:
        """
        Fetch all orders from Zerodha and update database
        Returns list of orders
        """
        kite = self.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            orders_data = kite.orders()

            # Get existing order IDs
            existing_order_ids = {o.order_id for o in self.db.query(Order.order_id).filter(
                Order.account_id == account_id
            ).all()}

            orders = []
            for item in orders_data:
                order_id = item.get("order_id", "")

                # Update existing order or create new one
                order = self.db.query(Order).filter(
                    Order.order_id == order_id
                ).first()

                if not order:
                    order = Order(
                        account_id=account_id,
                        order_id=order_id,
                        stock=item.get("tradingsymbol", ""),
                        exchange=item.get("exchange", "NSE"),
                        qty=item.get("quantity", 0),
                        price=item.get("average_price", 0),
                        order_type=item.get("order_type", "MARKET"),
                        transaction_type=item.get("transaction_type", "BUY"),
                        status=item.get("status", "PENDING"),
                        product=item.get("product", "CNC"),
                        validity=item.get("validity", "DAY"),
                        variety=item.get("variety", "regular"),
                        placed_at=datetime.fromtimestamp(item.get("order_timestamp", 0)),
                        updated_at=datetime.utcnow()
                    )
                    self.db.add(order)
                else:
                    # Update existing order
                    order.status = item.get("status", order.status)
                    order.updated_at = datetime.utcnow()

                orders.append(order)

            self.db.commit()
            logger.info(f"Fetched {len(orders)} orders for account {account_id}")
            return orders

        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            self.db.rollback()
            return self.db.query(Order).filter(Order.account_id == account_id).all()

    def fetch_portfolio_value(self, account_id: int) -> Dict[str, Any]:
        """
        Calculate total portfolio value for an account
        Returns dict with total_value, investment_value, day_pnl, etc.
        """
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()
        positions = self.db.query(Position).filter(Position.account_id == account_id).all()

        total_value = sum(h.current_value for h in holdings)
        investment_value = sum(h.qty * h.avg_price for h in holdings)

        day_pnl = sum(h.pnl for h in holdings) + sum(p.pnl for p in positions)
        day_pnl_percent = (day_pnl / investment_value * 100) if investment_value > 0 else 0

        return {
            "total_value": total_value,
            "investment_value": investment_value,
            "day_pnl": day_pnl,
            "day_pnl_percent": day_pnl_percent,
            "holdings_count": len(holdings),
            "positions_count": len(positions)
        }

    def place_order(self, account_id: int, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Place a new order on Zerodha
        params: {
            "tradingsymbol": "RELIANCE",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 10,
            "order_type": "MARKET",
            "product": "CNC",
            "price": 2000,  # Required for LIMIT orders
            "validity": "DAY",
            "variety": "regular"
        }
        Returns order response from Zerodha
        """
        kite = self.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            order_id = kite.place_order(
                tradingsymbol=params.get("tradingsymbol"),
                exchange=params.get("exchange", "NSE"),
                transaction_type=params.get("transaction_type"),
                quantity=params.get("quantity"),
                order_type=params.get("order_type", "MARKET"),
                product=params.get("product", "CNC"),
                price=params.get("price"),
                validity=params.get("validity", "DAY"),
                variety=params.get("variety", "regular")
            )

            logger.info(f"Order placed: {order_id}")
            return {"order_id": order_id, "status": "PLACED"}

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise

    def cancel_order(self, account_id: int, order_id: str) -> bool:
        """
        Cancel an order on Zerodha
        Returns True if successful
        """
        kite = self.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            kite.cancel_order(order_id=order_id, variety="regular")
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise

    def squareoff_position(self, account_id: int, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Square off a position
        params: {
            "tradingsymbol": "RELIANCE",
            "exchange": "NSE",
            "quantity": 10,
            "order_type": "MARKET",
            "product": "MIS"
        }
        """
        kite = self.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            # Determine transaction type based on position
            position = self.db.query(Position).filter(
                Position.account_id == account_id,
                Position.stock == params.get("tradingsymbol")
            ).first()

            if not position:
                raise ValueError("Position not found")

            transaction_type = "SELL" if position.qty > 0 else "BUY"
            quantity = abs(position.qty)

            order_id = kite.place_order(
                tradingsymbol=params.get("tradingsymbol"),
                exchange=params.get("exchange", "NSE"),
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=params.get("order_type", "MARKET"),
                product=params.get("product", "MIS"),
                variety="regular"
            )

            logger.info(f"Position squared off: {order_id}")
            return {"order_id": order_id, "status": "SQUARED_OFF"}

        except Exception as e:
            logger.error(f"Error squaring off position: {e}")
            raise

    def squareoff_all_positions(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Square off all open positions for an account
        Returns list of order responses
        """
        positions = self.db.query(Position).filter(Position.account_id == account_id).all()
        results = []

        for position in positions:
            try:
                result = self.squareoff_position(account_id, {
                    "tradingsymbol": position.stock,
                    "exchange": position.exchange,
                    "product": position.product
                })
                results.append(result)
            except Exception as e:
                logger.error(f"Error squaring off position {position.stock}: {e}")
                results.append({"stock": position.stock, "error": str(e)})

        return results

    def save_portfolio_snapshot(self, account_id: int) -> PortfolioSnapshot:
        """
        Save a portfolio snapshot for equity curve tracking
        """
        portfolio_value = self.fetch_portfolio_value(account_id)

        snapshot = PortfolioSnapshot(
            account_id=account_id,
            total_value=portfolio_value["total_value"],
            investment_value=portfolio_value["investment_value"],
            day_pnl=portfolio_value["day_pnl"],
            day_pnl_percent=portfolio_value["day_pnl_percent"],
            overall_pnl=portfolio_value["day_pnl"],  # Using day_pnl as overall for now
            overall_pnl_percent=portfolio_value["day_pnl_percent"],
            holdings_count=portfolio_value["holdings_count"],
            positions_count=portfolio_value["positions_count"],
            recorded_at=datetime.utcnow()
        )

        self.db.add(snapshot)
        self.db.commit()

        logger.info(f"Portfolio snapshot saved for account {account_id}")
        return snapshot

    def refresh_all_data(self, account_id: int) -> Dict[str, Any]:
        """
        Refresh all data (holdings, positions, orders) for an account
        """
        try:
            holdings = self.fetch_holdings(account_id)
            positions = self.fetch_positions(account_id)
            orders = self.fetch_orders(account_id)
            portfolio_value = self.fetch_portfolio_value(account_id)

            return {
                "holdings": len(holdings),
                "positions": len(positions),
                "orders": len(orders),
                "portfolio_value": portfolio_value
            }
        except Exception as e:
            logger.error(f"Error refreshing data for account {account_id}: {e}")
            raise
