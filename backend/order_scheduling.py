"""
Order Scheduling Manager for pyPortMan
Schedule orders for specific times (pre-market, post-market)
"""

import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, ScheduledOrder
from kite_manager import KiteManager

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


class OrderSchedulingManager:
    """Manager for scheduled orders"""

    # Market hours (IST)
    PRE_MARKET_START = time(9, 0)  # 9:00 AM
    PRE_MARKET_END = time(9, 15)  # 9:15 AM
    MARKET_START = time(9, 15)  # 9:15 AM
    MARKET_END = time(15, 30)  # 3:30 PM
    POST_MARKET_START = time(15, 40)  # 3:40 PM
    POST_MARKET_END = time(16, 0)  # 4:00 PM

    def __init__(self, db: Session):
        self.db = db
        self.kite_manager = KiteManager(db)

    def schedule_order(
        self,
        account_id: int,
        stock: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product: str,
        scheduled_time: datetime,
        time_type: str = "SPECIFIC",
        price: Optional[float] = None,
        validity: str = "DAY"
    ) -> ScheduledOrder:
        """
        Schedule a new order
        time_type: SPECIFIC, PRE_MARKET, POST_MARKET
        """
        # Calculate scheduled time based on time_type
        if time_type == "PRE_MARKET":
            scheduled_time = self._get_next_pre_market_time()
        elif time_type == "POST_MARKET":
            scheduled_time = self._get_next_post_market_time()

        # Validate scheduled time
        if scheduled_time <= datetime.utcnow():
            raise ValueError("Scheduled time must be in the future")

        scheduled_order = ScheduledOrder(
            account_id=account_id,
            stock=stock,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product=product,
            price=price,
            validity=validity,
            scheduled_time=scheduled_time,
            time_type=time_type,
            status="PENDING"
        )

        self.db.add(scheduled_order)
        self.db.commit()
        self.db.refresh(scheduled_order)

        logger.info(f"Scheduled order for {stock} at {scheduled_time}")
        return scheduled_order

    def _get_next_pre_market_time(self) -> datetime:
        """Get next pre-market session time"""
        now = datetime.utcnow()
        # Convert to IST (UTC+5:30)
        ist_now = now + timedelta(hours=5, minutes=30)

        # Get today's pre-market time
        today_pre_market = datetime.combine(
            ist_now.date(),
            self.PRE_MARKET_START
        )

        # If pre-market has passed, schedule for tomorrow
        if ist_now.time() >= self.PRE_MARKET_END:
            today_pre_market += timedelta(days=1)

        # Convert back to UTC
        return today_pre_market - timedelta(hours=5, minutes=30)

    def _get_next_post_market_time(self) -> datetime:
        """Get next post-market session time"""
        now = datetime.utcnow()
        # Convert to IST (UTC+5:30)
        ist_now = now + timedelta(hours=5, minutes=30)

        # Get today's post-market time
        today_post_market = datetime.combine(
            ist_now.date(),
            self.POST_MARKET_START
        )

        # If post-market has passed, schedule for tomorrow
        if ist_now.time() >= self.POST_MARKET_END:
            today_post_market += timedelta(days=1)

        # Convert back to UTC
        return today_post_market - timedelta(hours=5, minutes=30)

    def cancel_scheduled_order(self, scheduled_order_id: int) -> bool:
        """
        Cancel a scheduled order
        """
        scheduled_order = self.db.query(ScheduledOrder).filter(
            ScheduledOrder.id == scheduled_order_id
        ).first()

        if not scheduled_order:
            raise ValueError(f"Scheduled order {scheduled_order_id} not found")

        if scheduled_order.status != "PENDING":
            raise ValueError(f"Cannot cancel scheduled order with status {scheduled_order.status}")

        scheduled_order.status = "CANCELLED"
        scheduled_order.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Cancelled scheduled order {scheduled_order_id}")
        return True

    def execute_scheduled_orders(self) -> List[Dict[str, Any]]:
        """
        Execute all scheduled orders whose time has come
        Returns list of execution results
        """
        now = datetime.utcnow()

        # Get pending orders that are due
        scheduled_orders = self.db.query(ScheduledOrder).filter(
            ScheduledOrder.status == "PENDING",
            ScheduledOrder.scheduled_time <= now
        ).all()

        results = []

        for scheduled_order in scheduled_orders:
            try:
                # Prepare order parameters
                order_params = {
                    "tradingsymbol": scheduled_order.stock,
                    "exchange": scheduled_order.exchange,
                    "transaction_type": scheduled_order.transaction_type,
                    "quantity": scheduled_order.quantity,
                    "order_type": scheduled_order.order_type,
                    "product": scheduled_order.product,
                    "validity": scheduled_order.validity,
                    "variety": "regular"
                }

                # Add price for LIMIT orders
                if scheduled_order.order_type in ["LIMIT", "SL"]:
                    order_params["price"] = scheduled_order.price

                # Place the order
                result = self.kite_manager.place_order(
                    scheduled_order.account_id,
                    order_params
                )

                # Update scheduled order
                scheduled_order.status = "PLACED"
                scheduled_order.placed_order_id = result.get("order_id")
                scheduled_order.updated_at = datetime.utcnow()

                results.append({
                    "id": scheduled_order.id,
                    "stock": scheduled_order.stock,
                    "status": "PLACED",
                    "order_id": result.get("order_id")
                })

                logger.info(f"Executed scheduled order for {scheduled_order.stock}")

            except Exception as e:
                # Update scheduled order with error
                scheduled_order.status = "FAILED"
                scheduled_order.error_message = str(e)
                scheduled_order.updated_at = datetime.utcnow()

                results.append({
                    "id": scheduled_order.id,
                    "stock": scheduled_order.stock,
                    "status": "FAILED",
                    "error": str(e)
                })

                logger.error(f"Failed to execute scheduled order for {scheduled_order.stock}: {e}")

        self.db.commit()
        return results

    def get_scheduled_orders(
        self,
        account_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ScheduledOrder]:
        """
        Get scheduled orders with optional filters
        """
        query = self.db.query(ScheduledOrder)

        if account_id:
            query = query.filter(ScheduledOrder.account_id == account_id)

        if status:
            query = query.filter(ScheduledOrder.status == status)

        return query.order_by(ScheduledOrder.scheduled_time.asc()).all()

    def get_due_orders(self) -> List[ScheduledOrder]:
        """
        Get all scheduled orders that are due for execution
        """
        now = datetime.utcnow()
        return self.db.query(ScheduledOrder).filter(
            ScheduledOrder.status == "PENDING",
            ScheduledOrder.scheduled_time <= now
        ).all()

    def get_upcoming_orders(self, account_id: Optional[int] = None, hours: int = 24) -> List[ScheduledOrder]:
        """
        Get upcoming orders within the next N hours
        """
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)

        query = self.db.query(ScheduledOrder).filter(
            ScheduledOrder.status == "PENDING",
            ScheduledOrder.scheduled_time > now,
            ScheduledOrder.scheduled_time <= end_time
        )

        if account_id:
            query = query.filter(ScheduledOrder.account_id == account_id)

        return query.order_by(ScheduledOrder.scheduled_time.asc()).all()

    def get_scheduled_order_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of scheduled orders
        """
        query = self.db.query(ScheduledOrder)

        if account_id:
            query = query.filter(ScheduledOrder.account_id == account_id)

        total = query.count()
        pending = query.filter(ScheduledOrder.status == "PENDING").count()
        placed = query.filter(ScheduledOrder.status == "PLACED").count()
        failed = query.filter(ScheduledOrder.status == "FAILED").count()
        cancelled = query.filter(ScheduledOrder.status == "CANCELLED").count()

        # Count by time type
        pre_market = query.filter(ScheduledOrder.time_type == "PRE_MARKET").count()
        post_market = query.filter(ScheduledOrder.time_type == "POST_MARKET").count()
        specific = query.filter(ScheduledOrder.time_type == "SPECIFIC").count()

        return {
            "total": total,
            "pending": pending,
            "placed": placed,
            "failed": failed,
            "cancelled": cancelled,
            "pre_market": pre_market,
            "post_market": post_market,
            "specific": specific
        }

    def reschedule_order(
        self,
        scheduled_order_id: int,
        new_scheduled_time: datetime
    ) -> ScheduledOrder:
        """
        Reschedule an existing order to a new time
        """
        scheduled_order = self.db.query(ScheduledOrder).filter(
            ScheduledOrder.id == scheduled_order_id
        ).first()

        if not scheduled_order:
            raise ValueError(f"Scheduled order {scheduled_order_id} not found")

        if scheduled_order.status != "PENDING":
            raise ValueError(f"Cannot reschedule order with status {scheduled_order.status}")

        if new_scheduled_time <= datetime.utcnow():
            raise ValueError("New scheduled time must be in the future")

        scheduled_order.scheduled_time = new_scheduled_time
        scheduled_order.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(scheduled_order)

        logger.info(f"Rescheduled order {scheduled_order_id} to {new_scheduled_time}")
        return scheduled_order

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status
        """
        now = datetime.utcnow()
        # Convert to IST (UTC+5:30)
        ist_now = now + timedelta(hours=5, minutes=30)
        current_time = ist_now.time()

        # Determine market status
        if self.PRE_MARKET_START <= current_time < self.PRE_MARKET_END:
            status = "PRE_MARKET"
            is_open = False
        elif self.MARKET_START <= current_time < self.MARKET_END:
            status = "OPEN"
            is_open = True
        elif self.POST_MARKET_START <= current_time < self.POST_MARKET_END:
            status = "POST_MARKET"
            is_open = False
        else:
            status = "CLOSED"
            is_open = False

        # Calculate time to next market open
        today_open = datetime.combine(ist_now.date(), self.MARKET_START)
        if current_time < self.MARKET_START:
            time_to_open = (today_open - ist_now).total_seconds()
        else:
            tomorrow_open = today_open + timedelta(days=1)
            time_to_open = (tomorrow_open - ist_now).total_seconds()

        return {
            "status": status,
            "is_open": is_open,
            "current_time_ist": ist_now.strftime("%H:%M:%S"),
            "time_to_open_seconds": time_to_open,
            "time_to_open_minutes": time_to_open / 60,
            "pre_market_start": self.PRE_MARKET_START.strftime("%H:%M"),
            "market_start": self.MARKET_START.strftime("%H:%M"),
            "market_end": self.MARKET_END.strftime("%H:%M"),
            "post_market_start": self.POST_MARKET_START.strftime("%H:%M")
        }
