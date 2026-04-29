"""
Trailing Stop-Loss Manager for pyPortMan
Auto-adjusts stop-loss as price moves favorably
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, TrailingStopLoss, Holding, Position

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


class TrailingStopLossManager:
    """Manager for trailing stop-loss orders"""

    def __init__(self, db: Session):
        self.db = db

    def create_trailing_stop(
        self,
        account_id: int,
        stock: str,
        exchange: str,
        qty: int,
        initial_stop_loss: float,
        trail_amount: float,
        trail_type: str = "POINTS",
        position_type: str = "LONG"
    ) -> TrailingStopLoss:
        """
        Create a new trailing stop-loss order
        """
        # Get current price
        holding = self.db.query(Holding).filter(
            Holding.account_id == account_id,
            Holding.stock == stock
        ).first()

        if not holding:
            raise ValueError(f"Holding not found for {stock}")

        current_price = holding.ltp

        # Validate initial stop-loss
        if position_type == "LONG":
            if initial_stop_loss >= current_price:
                raise ValueError("Initial stop-loss must be below current price for LONG positions")
            highest_price = current_price
            lowest_price = 0
        else:
            if initial_stop_loss <= current_price:
                raise ValueError("Initial stop-loss must be above current price for SHORT positions")
            highest_price = 0
            lowest_price = current_price

        trailing_sl = TrailingStopLoss(
            account_id=account_id,
            stock=stock,
            exchange=exchange,
            qty=qty,
            initial_stop_loss=initial_stop_loss,
            current_stop_loss=initial_stop_loss,
            trail_amount=trail_amount,
            trail_type=trail_type,
            highest_price=highest_price,
            lowest_price=lowest_price,
            position_type=position_type,
            status="ACTIVE"
        )

        self.db.add(trailing_sl)
        self.db.commit()
        self.db.refresh(trailing_sl)

        logger.info(f"Created trailing stop-loss for {stock}: {initial_stop_loss}")
        return trailing_sl

    def update_trailing_stop(
        self,
        trailing_sl_id: int,
        trail_amount: Optional[float] = None,
        trail_type: Optional[str] = None
    ) -> TrailingStopLoss:
        """
        Update an existing trailing stop-loss
        """
        trailing_sl = self.db.query(TrailingStopLoss).filter(
            TrailingStopLoss.id == trailing_sl_id
        ).first()

        if not trailing_sl:
            raise ValueError(f"Trailing stop-loss {trailing_sl_id} not found")

        if trail_amount is not None:
            trailing_sl.trail_amount = trail_amount
        if trail_type is not None:
            trailing_sl.trail_type = trail_type

        trailing_sl.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(trailing_sl)

        logger.info(f"Updated trailing stop-loss {trailing_sl_id}")
        return trailing_sl

    def cancel_trailing_stop(self, trailing_sl_id: int) -> bool:
        """
        Cancel a trailing stop-loss
        """
        trailing_sl = self.db.query(TrailingStopLoss).filter(
            TrailingStopLoss.id == trailing_sl_id
        ).first()

        if not trailing_sl:
            raise ValueError(f"Trailing stop-loss {trailing_sl_id} not found")

        trailing_sl.status = "CANCELLED"
        trailing_sl.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Cancelled trailing stop-loss {trailing_sl_id}")
        return True

    def check_and_update_trailing_stops(self, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Check all active trailing stop-losses and update if needed
        Returns list of updated trailing stop-losses
        """
        query = self.db.query(TrailingStopLoss).filter(
            TrailingStopLoss.status == "ACTIVE"
        )

        if account_id:
            query = query.filter(TrailingStopLoss.account_id == account_id)

        trailing_sls = query.all()
        updated = []

        for tsl in trailing_sls:
            # Get current price
            holding = self.db.query(Holding).filter(
                Holding.account_id == tsl.account_id,
                Holding.stock == tsl.stock
            ).first()

            if not holding:
                logger.warning(f"Holding not found for {tsl.stock}, skipping trailing stop update")
                continue

            current_price = holding.ltp
            updated_sl = self._calculate_new_stop_loss(tsl, current_price)

            if updated_sl != tsl.current_stop_loss:
                tsl.current_stop_loss = updated_sl

                if tsl.position_type == "LONG":
                    tsl.highest_price = max(tsl.highest_price, current_price)
                else:
                    tsl.lowest_price = min(tsl.lowest_price, current_price)

                tsl.updated_at = datetime.utcnow()
                self.db.commit()

                updated.append({
                    "id": tsl.id,
                    "stock": tsl.stock,
                    "old_stop_loss": tsl.current_stop_loss,
                    "new_stop_loss": updated_sl,
                    "current_price": current_price
                })

                logger.info(f"Updated trailing stop-loss for {tsl.stock}: {updated_sl}")

        return updated

    def _calculate_new_stop_loss(self, tsl: TrailingStopLoss, current_price: float) -> float:
        """
        Calculate new stop-loss based on current price and trail settings
        """
        if tsl.position_type == "LONG":
            # For long positions, stop-loss trails upward
            if tsl.trail_type == "POINTS":
                new_sl = current_price - tsl.trail_amount
            else:  # PERCENTAGE
                new_sl = current_price * (1 - tsl.trail_amount / 100)

            # Only update if new SL is higher than current SL
            return max(new_sl, tsl.current_stop_loss)
        else:
            # For short positions, stop-loss trails downward
            if tsl.trail_type == "POINTS":
                new_sl = current_price + tsl.trail_amount
            else:  # PERCENTAGE
                new_sl = current_price * (1 + tsl.trail_amount / 100)

            # Only update if new SL is lower than current SL
            return min(new_sl, tsl.current_stop_loss)

    def check_triggers(self, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Check if any trailing stop-losses have been triggered
        Returns list of triggered trailing stop-losses
        """
        query = self.db.query(TrailingStopLoss).filter(
            TrailingStopLoss.status == "ACTIVE"
        )

        if account_id:
            query = query.filter(TrailingStopLoss.account_id == account_id)

        trailing_sls = query.all()
        triggered = []

        for tsl in trailing_sls:
            # Get current price
            holding = self.db.query(Holding).filter(
                Holding.account_id == tsl.account_id,
                Holding.stock == tsl.stock
            ).first()

            if not holding:
                continue

            current_price = holding.ltp

            # Check if triggered
            is_triggered = False
            if tsl.position_type == "LONG":
                is_triggered = current_price <= tsl.current_stop_loss
            else:
                is_triggered = current_price >= tsl.current_stop_loss

            if is_triggered:
                tsl.status = "TRIGGERED"
                tsl.triggered_at = datetime.utcnow()
                self.db.commit()

                triggered.append({
                    "id": tsl.id,
                    "stock": tsl.stock,
                    "stop_loss": tsl.current_stop_loss,
                    "triggered_price": current_price,
                    "qty": tsl.qty,
                    "position_type": tsl.position_type
                })

                logger.warning(f"Trailing stop-loss triggered for {tsl.stock} at {current_price}")

        return triggered

    def get_trailing_stops(
        self,
        account_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[TrailingStopLoss]:
        """
        Get trailing stop-losses with optional filters
        """
        query = self.db.query(TrailingStopLoss)

        if account_id:
            query = query.filter(TrailingStopLoss.account_id == account_id)

        if status:
            query = query.filter(TrailingStopLoss.status == status)

        return query.order_by(TrailingStopLoss.created_at.desc()).all()

    def get_trailing_stop_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of trailing stop-losses
        """
        query = self.db.query(TrailingStopLoss)

        if account_id:
            query = query.filter(TrailingStopLoss.account_id == account_id)

        total = query.count()
        active = query.filter(TrailingStopLoss.status == "ACTIVE").count()
        triggered = query.filter(TrailingStopLoss.status == "TRIGGERED").count()
        cancelled = query.filter(TrailingStopLoss.status == "CANCELLED").count()

        return {
            "total": total,
            "active": active,
            "triggered": triggered,
            "cancelled": cancelled
        }

    def get_trailing_stop_details(self, trailing_sl_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a trailing stop-loss
        """
        tsl = self.db.query(TrailingStopLoss).filter(
            TrailingStopLoss.id == trailing_sl_id
        ).first()

        if not tsl:
            raise ValueError(f"Trailing stop-loss {trailing_sl_id} not found")

        # Get current price
        holding = self.db.query(Holding).filter(
            Holding.account_id == tsl.account_id,
            Holding.stock == tsl.stock
        ).first()

        current_price = holding.ltp if holding else 0

        # Calculate distance to stop-loss
        if tsl.position_type == "LONG":
            distance = current_price - tsl.current_stop_loss
            distance_pct = (distance / current_price * 100) if current_price > 0 else 0
        else:
            distance = tsl.current_stop_loss - current_price
            distance_pct = (distance / current_price * 100) if current_price > 0 else 0

        return {
            "id": tsl.id,
            "stock": tsl.stock,
            "exchange": tsl.exchange,
            "qty": tsl.qty,
            "initial_stop_loss": tsl.initial_stop_loss,
            "current_stop_loss": tsl.current_stop_loss,
            "trail_amount": tsl.trail_amount,
            "trail_type": tsl.trail_type,
            "position_type": tsl.position_type,
            "status": tsl.status,
            "current_price": current_price,
            "distance_to_sl": distance,
            "distance_pct": distance_pct,
            "highest_price": tsl.highest_price,
            "lowest_price": tsl.lowest_price,
            "created_at": tsl.created_at.isoformat(),
            "updated_at": tsl.updated_at.isoformat(),
            "triggered_at": tsl.triggered_at.isoformat() if tsl.triggered_at else None
        }
