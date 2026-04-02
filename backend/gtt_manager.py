"""
GTT (Good Till Triggered) Order Manager for pyPortMan
Handles GTT order placement, modification, deletion, and status sync with Zerodha
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, GTTOrder

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


class GTTManager:
    """Manager for GTT (Good Till Triggered) orders"""

    def __init__(self, db: Session, kite_manager):
        self.db = db
        self.kite_manager = kite_manager

    def get_all_gtt(self, account_id: Optional[int] = None) -> List[GTTOrder]:
        """
        Fetch all GTT orders from database
        If account_id is provided, fetch only for that account
        """
        query = self.db.query(GTTOrder)
        if account_id:
            query = query.filter(GTTOrder.account_id == account_id)
        return query.order_by(GTTOrder.created_at.desc()).all()

    def get_gtt_by_id(self, gtt_id: str) -> Optional[GTTOrder]:
        """Get a specific GTT order by Zerodha GTT ID"""
        return self.db.query(GTTOrder).filter(GTTOrder.gtt_id == gtt_id).first()

    def place_gtt(self, account_id: int, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Place a single GTT order on Zerodha
        params: {
            "stock": "RELIANCE",
            "exchange": "NSE",
            "qty": 10,
            "buy_price": 2000,
            "target_price": 2100,
            "sl_price": 1950,
            "allocation_pct": 10
        }
        Returns: { gtt_id, status }
        """
        kite = self.kite_manager.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            # Create two-leg GTT order (target + stop loss)
            gtt_params = {
                "tradingsymbol": params.get("stock"),
                "exchange": params.get("exchange", "NSE"),
                "last_price": params.get("buy_price"),
                "trigger": {
                    "type": "two-leg",
                    "first": {
                        "type": "BUY",
                        "price": params.get("buy_price"),
                        "quantity": params.get("qty"),
                        "exchange": params.get("exchange", "NSE"),
                        "tradingsymbol": params.get("stock"),
                        "order_type": "MARKET",
                        "product": "CNC",
                        "transaction_type": "BUY"
                    },
                    "second": {
                        "type": "SELL",
                        "price": params.get("target_price"),
                        "quantity": params.get("qty"),
                        "exchange": params.get("exchange", "NSE"),
                        "tradingsymbol": params.get("stock"),
                        "order_type": "LIMIT",
                        "product": "CNC",
                        "transaction_type": "SELL"
                    }
                }
            }

            # Place GTT order
            gtt_response = kite.place_gtt(gtt_params)

            gtt_id = gtt_response.get("id")
            if not gtt_id:
                raise ValueError("Failed to place GTT order: No GTT ID returned")

            # Save to database
            gtt_order = GTTOrder(
                account_id=account_id,
                gtt_id=gtt_id,
                stock=params.get("stock"),
                exchange=params.get("exchange", "NSE"),
                qty=params.get("qty"),
                buy_price=params.get("buy_price"),
                target_price=params.get("target_price"),
                sl_price=params.get("sl_price"),
                allocation_pct=params.get("allocation_pct", 0),
                status="ACTIVE",
                trigger_type="TWO_LEG",
                created_at=datetime.utcnow()
            )
            self.db.add(gtt_order)
            self.db.commit()

            logger.info(f"GTT order placed: {gtt_id} for {params.get('stock')}")
            return {"gtt_id": gtt_id, "status": "ACTIVE"}

        except Exception as e:
            logger.error(f"Error placing GTT order: {e}")
            self.db.rollback()
            raise

    def modify_gtt(self, account_id: int, gtt_id: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Modify an existing GTT order
        params: {
            "target_price": 2150,
            "sl_price": 1900,
            "qty": 15
        }
        """
        kite = self.kite_manager.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            # Get existing GTT order
            gtt_order = self.get_gtt_by_id(gtt_id)
            if not gtt_order:
                raise ValueError(f"GTT order {gtt_id} not found")

            # Build modified GTT params
            gtt_params = {
                "tradingsymbol": gtt_order.stock,
                "exchange": gtt_order.exchange,
                "last_price": params.get("buy_price", gtt_order.buy_price),
                "trigger": {
                    "type": "two-leg",
                    "first": {
                        "type": "BUY",
                        "price": params.get("buy_price", gtt_order.buy_price),
                        "quantity": params.get("qty", gtt_order.qty),
                        "exchange": gtt_order.exchange,
                        "tradingsymbol": gtt_order.stock,
                        "order_type": "MARKET",
                        "product": "CNC",
                        "transaction_type": "BUY"
                    },
                    "second": {
                        "type": "SELL",
                        "price": params.get("target_price", gtt_order.target_price),
                        "quantity": params.get("qty", gtt_order.qty),
                        "exchange": gtt_order.exchange,
                        "tradingsymbol": gtt_order.stock,
                        "order_type": "LIMIT",
                        "product": "CNC",
                        "transaction_type": "SELL"
                    }
                }
            }

            # Modify GTT order
            kite.update_gtt(gtt_id, gtt_params)

            # Update database
            if "target_price" in params:
                gtt_order.target_price = params["target_price"]
            if "sl_price" in params:
                gtt_order.sl_price = params["sl_price"]
            if "qty" in params:
                gtt_order.qty = params["qty"]
            if "buy_price" in params:
                gtt_order.buy_price = params["buy_price"]
            if "allocation_pct" in params:
                gtt_order.allocation_pct = params["allocation_pct"]

            gtt_order.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"GTT order modified: {gtt_id}")
            return {"gtt_id": gtt_id, "status": "MODIFIED"}

        except Exception as e:
            logger.error(f"Error modifying GTT order: {e}")
            self.db.rollback()
            raise

    def delete_gtt(self, account_id: int, gtt_id: str) -> bool:
        """
        Delete a GTT order
        """
        kite = self.kite_manager.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available. Token may be expired.")

        try:
            # Delete from Zerodha
            kite.delete_gtt(gtt_id)

            # Delete from database
            gtt_order = self.get_gtt_by_id(gtt_id)
            if gtt_order:
                self.db.delete(gtt_order)
                self.db.commit()

            logger.info(f"GTT order deleted: {gtt_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting GTT order: {e}")
            self.db.rollback()
            raise

    def place_bulk_gtt(self, account_id: int, stock_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Place GTT orders for multiple stocks for a single account
        stock_list: [
            {
                "stock": "RELIANCE",
                "exchange": "NSE",
                "qty": 10,
                "buy_price": 2000,
                "target_price": 2100,
                "sl_price": 1950,
                "allocation_pct": 10
            },
            ...
        ]
        Returns: List of results for each stock
        """
        results = []
        for stock_params in stock_list:
            try:
                result = self.place_gtt(account_id, stock_params)
                results.append({
                    "stock": stock_params.get("stock"),
                    "status": "SUCCESS",
                    "gtt_id": result.get("gtt_id")
                })
            except Exception as e:
                logger.error(f"Error placing GTT for {stock_params.get('stock')}: {e}")
                results.append({
                    "stock": stock_params.get("stock"),
                    "status": "FAILED",
                    "error": str(e)
                })

        return results

    def place_gtt_all_accounts(self, stock_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Place same GTT orders across ALL accounts
        Returns: Summary of results
        """
        accounts = self.kite_manager.get_all_accounts()
        if not accounts:
            raise ValueError("No active accounts found")

        results = {
            "total_accounts": len(accounts),
            "total_stocks": len(stock_list),
            "account_results": []
        }

        for account in accounts:
            try:
                account_result = self.place_bulk_gtt(account.id, stock_list)
                results["account_results"].append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "results": account_result
                })
            except Exception as e:
                logger.error(f"Error placing GTT for account {account.id}: {e}")
                results["account_results"].append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "error": str(e)
                })

        return results

    def sync_gtt_status(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Sync GTT status from Zerodha to our database
        If account_id is provided, sync only for that account
        """
        accounts = []
        if account_id:
            account = self.kite_manager.get_account(account_id)
            if account:
                accounts = [account]
        else:
            accounts = self.kite_manager.get_all_accounts()

        synced_count = 0
        errors = []

        for account in accounts:
            try:
                kite = self.kite_manager.get_kite(account.id)
                if not kite:
                    errors.append(f"Account {account.id}: Token expired")
                    continue

                # Fetch all GTT orders from Zerodha
                z_gtt_orders = kite.get_gtts()

                for z_gtt in z_gtt_orders:
                    z_gtt_id = z_gtt.get("id")
                    z_status = z_gtt.get("status", "ACTIVE").upper()

                    # Find existing GTT in database
                    gtt_order = self.db.query(GTTOrder).filter(
                        GTTOrder.gtt_id == z_gtt_id
                    ).first()

                    if gtt_order:
                        # Update status if changed
                        if gtt_order.status != z_status:
                            gtt_order.status = z_status
                            if z_status == "TRIGGERED":
                                gtt_order.triggered_at = datetime.utcnow()
                            gtt_order.updated_at = datetime.utcnow()
                            synced_count += 1
                    else:
                        # Create new GTT entry if not exists
                        # Extract trigger info
                        trigger = z_gtt.get("trigger", {})
                        condition = trigger.get("condition", {})
                        orders = trigger.get("orders", [])

                        # Try to extract stock info
                        tradingsymbol = z_gtt.get("tradingsymbol", "")
                        exchange = z_gtt.get("exchange", "NSE")

                        # Extract quantity and prices from orders
                        qty = 0
                        buy_price = 0
                        target_price = 0
                        sl_price = 0

                        for order in orders:
                            if order.get("transaction_type") == "BUY":
                                qty = order.get("quantity", 0)
                                buy_price = order.get("price", 0)
                            elif order.get("transaction_type") == "SELL":
                                if order.get("order_type") == "LIMIT":
                                    target_price = order.get("price", 0)
                                else:
                                    sl_price = order.get("price", 0)

                        new_gtt = GTTOrder(
                            account_id=account.id,
                            gtt_id=z_gtt_id,
                            stock=tradingsymbol,
                            exchange=exchange,
                            qty=qty,
                            buy_price=buy_price,
                            target_price=target_price,
                            sl_price=sl_price,
                            allocation_pct=0,
                            status=z_status,
                            trigger_type="TWO_LEG",
                            created_at=datetime.fromtimestamp(z_gtt.get("created_at", 0))
                        )
                        self.db.add(new_gtt)
                        synced_count += 1

                self.db.commit()

            except Exception as e:
                logger.error(f"Error syncing GTT for account {account.id}: {e}")
                errors.append(f"Account {account.id}: {str(e)}")

        return {
            "synced_count": synced_count,
            "errors": errors
        }

    def get_gtt_summary(self) -> Dict[str, Any]:
        """
        Get summary of all GTT orders
        """
        all_gtt = self.get_all_gtt()

        active_count = sum(1 for g in all_gtt if g.status == "ACTIVE")
        triggered_count = sum(1 for g in all_gtt if g.status == "TRIGGERED")
        cancelled_count = sum(1 for g in all_gtt if g.status == "CANCELLED")
        expired_count = sum(1 for g in all_gtt if g.status == "EXPIRED")

        # Get unique accounts
        account_ids = set(g.account_id for g in all_gtt)

        # Estimate capital deployed
        capital_deployed = sum(
            g.qty * g.buy_price for g in all_gtt if g.status == "ACTIVE"
        )

        return {
            "total_orders": len(all_gtt),
            "active_orders": active_count,
            "triggered_orders": triggered_count,
            "cancelled_orders": cancelled_count,
            "expired_orders": expired_count,
            "accounts_covered": len(account_ids),
            "estimated_capital": capital_deployed
        }
