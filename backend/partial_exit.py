"""
Partial Exit Strategy Manager for pyPortMan
Configure multiple exit points (e.g., 50% at target1, 50% at target2)
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, PartialExitStrategy, PartialExitPoint, Holding
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


class PartialExitStrategyManager:
    """Manager for partial exit strategies"""

    def __init__(self, db: Session):
        self.db = db
        self.kite_manager = KiteManager(db)

    def create_strategy(
        self,
        account_id: int,
        stock: str,
        exchange: str,
        position_type: str,
        total_quantity: int,
        exit_points: List[Dict[str, Any]]
    ) -> PartialExitStrategy:
        """
        Create a new partial exit strategy
        exit_points: List of dicts with keys: sequence, quantity, quantity_pct, target_price, stop_loss
        """
        # Validate holding exists
        holding = self.db.query(Holding).filter(
            Holding.account_id == account_id,
            Holding.stock == stock
        ).first()

        if not holding:
            raise ValueError(f"Holding not found for {stock}")

        # Validate total quantity
        if position_type == "LONG" and holding.qty < total_quantity:
            raise ValueError(f"Insufficient quantity. Available: {holding.qty}, Requested: {total_quantity}")
        elif position_type == "SHORT" and holding.qty > -total_quantity:
            raise ValueError(f"Insufficient quantity for short position")

        # Validate exit points
        total_exit_qty = 0
        for i, point in enumerate(exit_points):
            if point.get("sequence") != i + 1:
                raise ValueError(f"Exit point sequence must be 1, 2, 3... in order")

            qty = point.get("quantity", 0)
            qty_pct = point.get("quantity_pct", 0)

            if qty_pct > 0:
                qty = int(total_quantity * qty_pct / 100)
                point["quantity"] = qty

            total_exit_qty += qty

            if not point.get("target_price"):
                raise ValueError(f"Target price required for exit point {i + 1}")

        if total_exit_qty != total_quantity:
            raise ValueError(f"Total exit quantity ({total_exit_qty}) must equal total quantity ({total_quantity})")

        # Create strategy
        strategy = PartialExitStrategy(
            account_id=account_id,
            stock=stock,
            exchange=exchange,
            position_type=position_type,
            total_quantity=total_quantity,
            status="ACTIVE"
        )

        self.db.add(strategy)
        self.db.flush()  # Get the ID

        # Create exit points
        for point in exit_points:
            exit_point = PartialExitPoint(
                strategy_id=strategy.id,
                sequence=point["sequence"],
                quantity=point["quantity"],
                quantity_pct=point.get("quantity_pct"),
                target_price=point["target_price"],
                stop_loss=point.get("stop_loss"),
                status="PENDING"
            )
            self.db.add(exit_point)

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Created partial exit strategy for {stock} with {len(exit_points)} exit points")
        return strategy

    def update_strategy(
        self,
        strategy_id: int,
        **kwargs
    ) -> PartialExitStrategy:
        """
        Update an existing partial exit strategy
        """
        strategy = self.db.query(PartialExitStrategy).filter(
            PartialExitStrategy.id == strategy_id
        ).first()

        if not strategy:
            raise ValueError(f"Partial exit strategy {strategy_id} not found")

        if strategy.status != "ACTIVE":
            raise ValueError(f"Cannot update strategy with status {strategy.status}")

        # Update provided fields
        for field, value in kwargs.items():
            if hasattr(strategy, field) and value is not None:
                setattr(strategy, field, value)

        strategy.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Updated partial exit strategy {strategy_id}")
        return strategy

    def cancel_strategy(self, strategy_id: int) -> bool:
        """
        Cancel a partial exit strategy
        """
        strategy = self.db.query(PartialExitStrategy).filter(
            PartialExitStrategy.id == strategy_id
        ).first()

        if not strategy:
            raise ValueError(f"Partial exit strategy {strategy_id} not found")

        strategy.status = "CANCELLED"
        strategy.updated_at = datetime.utcnow()

        # Cancel all pending exit points
        for point in strategy.exit_points:
            if point.status == "PENDING":
                point.status = "CANCELLED"

        self.db.commit()

        logger.info(f"Cancelled partial exit strategy {strategy_id}")
        return True

    def check_and_execute_exits(self, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Check all active strategies and execute exits if targets are reached
        Returns list of executed exits
        """
        query = self.db.query(PartialExitStrategy).filter(
            PartialExitStrategy.status == "ACTIVE"
        )

        if account_id:
            query = query.filter(PartialExitStrategy.account_id == account_id)

        strategies = query.all()
        executed = []

        for strategy in strategies:
            # Get current price
            holding = self.db.query(Holding).filter(
                Holding.account_id == strategy.account_id,
                Holding.stock == strategy.stock
            ).first()

            if not holding:
                logger.warning(f"Holding not found for {strategy.stock}, skipping exit check")
                continue

            current_price = holding.ltp

            # Check each exit point in sequence
            for point in strategy.exit_points:
                if point.status != "PENDING":
                    continue

                # Check if previous exit points are executed
                previous_points = [p for p in strategy.exit_points if p.sequence < point.sequence]
                if not all(p.status == "EXECUTED" for p in previous_points):
                    continue

                # Check if target is reached
                target_reached = False
                if strategy.position_type == "LONG":
                    target_reached = current_price >= point.target_price
                else:
                    target_reached = current_price <= point.target_price

                if target_reached:
                    try:
                        # Execute the exit
                        result = self._execute_exit(strategy, point)

                        executed.append({
                            "strategy_id": strategy.id,
                            "stock": strategy.stock,
                            "exit_point_id": point.id,
                            "sequence": point.sequence,
                            "quantity": point.quantity,
                            "target_price": point.target_price,
                            "executed_price": current_price,
                            "order_id": result.get("order_id")
                        })

                        logger.info(f"Executed exit point {point.sequence} for {strategy.stock}")

                    except Exception as e:
                        logger.error(f"Failed to execute exit for {strategy.stock}: {e}")

        return executed

    def _execute_exit(
        self,
        strategy: PartialExitStrategy,
        point: PartialExitPoint
    ) -> Dict[str, Any]:
        """
        Execute a single exit point
        """
        # Determine transaction type
        if strategy.position_type == "LONG":
            transaction_type = "SELL"
        else:
            transaction_type = "BUY"

        # Prepare order parameters
        order_params = {
            "tradingsymbol": strategy.stock,
            "exchange": strategy.exchange,
            "transaction_type": transaction_type,
            "quantity": point.quantity,
            "order_type": "MARKET",
            "product": "CNC",
            "validity": "DAY",
            "variety": "regular"
        }

        # Place the order
        result = self.kite_manager.place_order(
            strategy.account_id,
            order_params
        )

        # Update exit point
        point.status = "EXECUTED"
        point.executed_at = datetime.utcnow()
        point.order_id = result.get("order_id")

        # Check if all exits are executed
        all_executed = all(p.status == "EXECUTED" for p in strategy.exit_points)
        if all_executed:
            strategy.status = "COMPLETED"

        self.db.commit()

        return result

    def get_strategies(
        self,
        account_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[PartialExitStrategy]:
        """
        Get partial exit strategies with optional filters
        """
        query = self.db.query(PartialExitStrategy)

        if account_id:
            query = query.filter(PartialExitStrategy.account_id == account_id)

        if status:
            query = query.filter(PartialExitStrategy.status == status)

        return query.order_by(PartialExitStrategy.created_at.desc()).all()

    def get_strategy_details(self, strategy_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a partial exit strategy
        """
        strategy = self.db.query(PartialExitStrategy).filter(
            PartialExitStrategy.id == strategy_id
        ).first()

        if not strategy:
            raise ValueError(f"Partial exit strategy {strategy_id} not found")

        # Get current price
        holding = self.db.query(Holding).filter(
            Holding.account_id == strategy.account_id,
            Holding.stock == strategy.stock
        ).first()

        current_price = holding.ltp if holding else 0

        # Calculate progress
        executed_qty = sum(p.quantity for p in strategy.exit_points if p.status == "EXECUTED")
        remaining_qty = strategy.total_quantity - executed_qty
        progress_pct = (executed_qty / strategy.total_quantity * 100) if strategy.total_quantity > 0 else 0

        # Format exit points
        exit_points_data = []
        for point in strategy.exit_points:
            distance = point.target_price - current_price
            distance_pct = (distance / current_price * 100) if current_price > 0 else 0

            exit_points_data.append({
                "sequence": point.sequence,
                "quantity": point.quantity,
                "quantity_pct": point.quantity_pct,
                "target_price": point.target_price,
                "stop_loss": point.stop_loss,
                "status": point.status,
                "executed_at": point.executed_at.isoformat() if point.executed_at else None,
                "order_id": point.order_id,
                "distance": distance,
                "distance_pct": distance_pct
            })

        return {
            "id": strategy.id,
            "stock": strategy.stock,
            "exchange": strategy.exchange,
            "position_type": strategy.position_type,
            "total_quantity": strategy.total_quantity,
            "status": strategy.status,
            "current_price": current_price,
            "executed_quantity": executed_qty,
            "remaining_quantity": remaining_qty,
            "progress_pct": progress_pct,
            "exit_points": exit_points_data,
            "created_at": strategy.created_at.isoformat(),
            "updated_at": strategy.updated_at.isoformat()
        }

    def get_strategy_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of partial exit strategies
        """
        query = self.db.query(PartialExitStrategy)

        if account_id:
            query = query.filter(PartialExitStrategy.account_id == account_id)

        total = query.count()
        active = query.filter(PartialExitStrategy.status == "ACTIVE").count()
        completed = query.filter(PartialExitStrategy.status == "COMPLETED").count()
        cancelled = query.filter(PartialExitStrategy.status == "CANCELLED").count()

        return {
            "total": total,
            "active": active,
            "completed": completed,
            "cancelled": cancelled
        }

    def get_next_exit(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the next pending exit point for a strategy
        """
        strategy = self.db.query(PartialExitStrategy).filter(
            PartialExitStrategy.id == strategy_id
        ).first()

        if not strategy or strategy.status != "ACTIVE":
            return None

        # Find next pending exit point
        for point in sorted(strategy.exit_points, key=lambda p: p.sequence):
            if point.status == "PENDING":
                # Check if previous exits are executed
                previous_points = [p for p in strategy.exit_points if p.sequence < point.sequence]
                if all(p.status == "EXECUTED" for p in previous_points):
                    # Get current price
                    holding = self.db.query(Holding).filter(
                        Holding.account_id == strategy.account_id,
                        Holding.stock == strategy.stock
                    ).first()

                    current_price = holding.ltp if holding else 0
                    distance = point.target_price - current_price
                    distance_pct = (distance / current_price * 100) if current_price > 0 else 0

                    return {
                        "sequence": point.sequence,
                        "quantity": point.quantity,
                        "quantity_pct": point.quantity_pct,
                        "target_price": point.target_price,
                        "current_price": current_price,
                        "distance": distance,
                        "distance_pct": distance_pct
                    }

        return None
