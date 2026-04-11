"""
Position Sizing Module for pyPortMan
Implements various position sizing strategies for risk management
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from kiteconnect import KiteConnect

from models import Account, Holding, Position

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


class PositionSizingManager:
    """Manager for calculating position sizes using various strategies"""

    def __init__(self, db: Session):
        self.db = db

    def get_account_capital(self, account_id: int) -> Dict[str, float]:
        """
        Get available capital for an account
        Returns: {total_capital, available_margin, used_margin}
        """
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        # Get holdings value
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()
        holdings_value = sum(h.current_value for h in holdings)

        # Get positions value
        positions = self.db.query(Position).filter(Position.account_id == account_id).all()
        positions_value = sum(abs(p.qty * p.ltp) for p in positions)

        # For now, use holdings + positions as total capital
        # In production, this should come from KiteConnect margins API
        total_capital = holdings_value + positions_value
        used_margin = positions_value
        available_margin = total_capital - used_margin

        return {
            "total_capital": total_capital,
            "available_margin": available_margin,
            "used_margin": used_margin,
            "holdings_value": holdings_value
        }

    def calculate_fixed_fractional(
        self,
        account_id: int,
        stock_price: float,
        risk_per_trade_pct: float = 2.0,
        stop_loss_pct: float = 5.0
    ) -> Dict[str, Any]:
        """
        Calculate position size using Fixed Fractional method
        Risk a fixed percentage of capital per trade

        Args:
            account_id: Account ID
            stock_price: Current stock price
            risk_per_trade_pct: Risk percentage per trade (default 2%)
            stop_loss_pct: Stop loss percentage (default 5%)

        Returns: {quantity, risk_amount, position_value, capital_used_pct}
        """
        capital = self.get_account_capital(account_id)
        total_capital = capital["total_capital"]

        if total_capital <= 0:
            raise ValueError("Insufficient capital")

        # Calculate risk amount
        risk_amount = total_capital * (risk_per_trade_pct / 100)

        # Calculate stop loss amount per share
        stop_loss_amount = stock_price * (stop_loss_pct / 100)

        # Calculate quantity based on risk
        quantity = int(risk_amount / stop_loss_amount)

        # Calculate position value
        position_value = quantity * stock_price

        # Calculate capital used percentage
        capital_used_pct = (position_value / total_capital * 100) if total_capital > 0 else 0

        return {
            "strategy": "fixed_fractional",
            "quantity": quantity,
            "risk_amount": risk_amount,
            "position_value": position_value,
            "capital_used_pct": capital_used_pct,
            "stop_loss_pct": stop_loss_pct,
            "risk_per_trade_pct": risk_per_trade_pct,
            "total_capital": total_capital
        }

    def calculate_kelly_criterion(
        self,
        account_id: int,
        stock_price: float,
        win_rate: float = 0.55,
        avg_win_pct: float = 10.0,
        avg_loss_pct: float = 5.0,
        kelly_fraction: float = 0.25
    ) -> Dict[str, Any]:
        """
        Calculate position size using Kelly Criterion
        Optimal position sizing based on win rate and risk/reward ratio

        Args:
            account_id: Account ID
            stock_price: Current stock price
            win_rate: Historical win rate (0-1, default 0.55)
            avg_win_pct: Average win percentage (default 10%)
            avg_loss_pct: Average loss percentage (default 5%)
            kelly_fraction: Fraction of Kelly to use (0-1, default 0.25 for safety)

        Returns: {quantity, kelly_percentage, position_value, capital_used_pct}
        """
        capital = self.get_account_capital(account_id)
        total_capital = capital["total_capital"]

        if total_capital <= 0:
            raise ValueError("Insufficient capital")

        # Calculate Kelly percentage
        # Kelly = (W * R - (1 - W)) / R
        # where W = win rate, R = risk/reward ratio
        risk_reward_ratio = avg_win_pct / avg_loss_pct
        kelly_pct = (win_rate * risk_reward_ratio - (1 - win_rate)) / risk_reward_ratio

        # Apply Kelly fraction for safety (half-Kelly, quarter-Kelly, etc.)
        adjusted_kelly_pct = kelly_pct * kelly_fraction

        # Calculate position value
        position_value = total_capital * adjusted_kelly_pct

        # Calculate quantity
        quantity = int(position_value / stock_price)

        # Calculate actual capital used percentage
        capital_used_pct = (position_value / total_capital * 100) if total_capital > 0 else 0

        return {
            "strategy": "kelly_criterion",
            "quantity": quantity,
            "kelly_percentage": kelly_pct * 100,
            "adjusted_kelly_percentage": adjusted_kelly_pct * 100,
            "position_value": position_value,
            "capital_used_pct": capital_used_pct,
            "win_rate": win_rate,
            "risk_reward_ratio": risk_reward_ratio,
            "kelly_fraction": kelly_fraction,
            "total_capital": total_capital
        }

    def calculate_volatility_based(
        self,
        account_id: int,
        stock_price: float,
        atr: float,
        risk_per_trade_pct: float = 2.0,
        atr_multiplier: float = 2.0
    ) -> Dict[str, Any]:
        """
        Calculate position size using Volatility-based method
        Adjust position size based on market volatility (ATR)

        Args:
            account_id: Account ID
            stock_price: Current stock price
            atr: Average True Range (volatility measure)
            risk_per_trade_pct: Risk percentage per trade (default 2%)
            atr_multiplier: ATR multiplier for stop loss (default 2.0)

        Returns: {quantity, risk_amount, position_value, capital_used_pct, stop_loss_price}
        """
        capital = self.get_account_capital(account_id)
        total_capital = capital["total_capital"]

        if total_capital <= 0:
            raise ValueError("Insufficient capital")

        if atr <= 0:
            raise ValueError("ATR must be positive")

        # Calculate risk amount
        risk_amount = total_capital * (risk_per_trade_pct / 100)

        # Calculate stop loss using ATR
        stop_loss_amount = atr * atr_multiplier

        # Calculate quantity based on risk
        quantity = int(risk_amount / stop_loss_amount)

        # Calculate position value
        position_value = quantity * stock_price

        # Calculate stop loss price
        stop_loss_price = stock_price - stop_loss_amount

        # Calculate capital used percentage
        capital_used_pct = (position_value / total_capital * 100) if total_capital > 0 else 0

        return {
            "strategy": "volatility_based",
            "quantity": quantity,
            "risk_amount": risk_amount,
            "position_value": position_value,
            "capital_used_pct": capital_used_pct,
            "stop_loss_price": stop_loss_price,
            "stop_loss_amount": stop_loss_amount,
            "atr": atr,
            "atr_multiplier": atr_multiplier,
            "risk_per_trade_pct": risk_per_trade_pct,
            "total_capital": total_capital
        }

    def calculate_fixed_amount(
        self,
        account_id: int,
        stock_price: float,
        fixed_amount: float
    ) -> Dict[str, Any]:
        """
        Calculate position size using Fixed Amount method
        Use a fixed amount per trade

        Args:
            account_id: Account ID
            stock_price: Current stock price
            fixed_amount: Fixed amount to invest per trade

        Returns: {quantity, position_value, capital_used_pct}
        """
        capital = self.get_account_capital(account_id)
        total_capital = capital["total_capital"]

        if total_capital <= 0:
            raise ValueError("Insufficient capital")

        if fixed_amount <= 0:
            raise ValueError("Fixed amount must be positive")

        # Calculate quantity
        quantity = int(fixed_amount / stock_price)

        # Calculate position value
        position_value = quantity * stock_price

        # Calculate capital used percentage
        capital_used_pct = (position_value / total_capital * 100) if total_capital > 0 else 0

        return {
            "strategy": "fixed_amount",
            "quantity": quantity,
            "position_value": position_value,
            "capital_used_pct": capital_used_pct,
            "fixed_amount": fixed_amount,
            "total_capital": total_capital
        }

    def calculate_percentage_based(
        self,
        account_id: int,
        stock_price: float,
        allocation_pct: float
    ) -> Dict[str, Any]:
        """
        Calculate position size using Percentage-based allocation
        Allocate a fixed percentage of capital to the position

        Args:
            account_id: Account ID
            stock_price: Current stock price
            allocation_pct: Percentage of capital to allocate (0-100)

        Returns: {quantity, position_value, capital_used_pct}
        """
        capital = self.get_account_capital(account_id)
        total_capital = capital["total_capital"]

        if total_capital <= 0:
            raise ValueError("Insufficient capital")

        if allocation_pct <= 0 or allocation_pct > 100:
            raise ValueError("Allocation percentage must be between 0 and 100")

        # Calculate position value
        position_value = total_capital * (allocation_pct / 100)

        # Calculate quantity
        quantity = int(position_value / stock_price)

        # Calculate capital used percentage
        capital_used_pct = allocation_pct

        return {
            "strategy": "percentage_based",
            "quantity": quantity,
            "position_value": position_value,
            "capital_used_pct": capital_used_pct,
            "allocation_pct": allocation_pct,
            "total_capital": total_capital
        }

    def compare_strategies(
        self,
        account_id: int,
        stock_price: float,
        atr: Optional[float] = None,
        risk_per_trade_pct: float = 2.0,
        stop_loss_pct: float = 5.0,
        win_rate: float = 0.55,
        avg_win_pct: float = 10.0,
        avg_loss_pct: float = 5.0,
        fixed_amount: Optional[float] = None,
        allocation_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compare all position sizing strategies for a given stock

        Returns: {strategies: [...], recommended: {...}}
        """
        strategies = []

        # Fixed Fractional
        try:
            strategies.append(self.calculate_fixed_fractional(
                account_id, stock_price, risk_per_trade_pct, stop_loss_pct
            ))
        except Exception as e:
            logger.error(f"Error calculating fixed fractional: {e}")

        # Kelly Criterion
        try:
            strategies.append(self.calculate_kelly_criterion(
                account_id, stock_price, win_rate, avg_win_pct, avg_loss_pct
            ))
        except Exception as e:
            logger.error(f"Error calculating Kelly criterion: {e}")

        # Volatility-based (if ATR provided)
        if atr:
            try:
                strategies.append(self.calculate_volatility_based(
                    account_id, stock_price, atr, risk_per_trade_pct
                ))
            except Exception as e:
                logger.error(f"Error calculating volatility-based: {e}")

        # Fixed Amount (if provided)
        if fixed_amount:
            try:
                strategies.append(self.calculate_fixed_amount(
                    account_id, stock_price, fixed_amount
                ))
            except Exception as e:
                logger.error(f"Error calculating fixed amount: {e}")

        # Percentage-based (if provided)
        if allocation_pct:
            try:
                strategies.append(self.calculate_percentage_based(
                    account_id, stock_price, allocation_pct
                ))
            except Exception as e:
                logger.error(f"Error calculating percentage-based: {e}")

        # Find recommended strategy (moderate risk)
        recommended = None
        if strategies:
            # Prefer fixed fractional as default recommendation
            for s in strategies:
                if s["strategy"] == "fixed_fractional":
                    recommended = s
                    break
            if not recommended:
                recommended = strategies[0]

        return {
            "stock_price": stock_price,
            "strategies": strategies,
            "recommended": recommended,
            "account_id": account_id
        }

    def get_risk_summary(self, account_id: int) -> Dict[str, Any]:
        """
        Get risk summary for an account
        Returns current exposure, open positions risk, etc.
        """
        capital = self.get_account_capital(account_id)

        # Get positions
        positions = self.db.query(Position).filter(Position.account_id == account_id).all()

        total_position_value = sum(abs(p.qty * p.ltp) for p in positions)
        total_unrealized_pnl = sum(p.pnl for p in positions)

        # Calculate exposure percentage
        exposure_pct = (total_position_value / capital["total_capital"] * 100) if capital["total_capital"] > 0 else 0

        # Count winning and losing positions
        winning_positions = sum(1 for p in positions if p.pnl > 0)
        losing_positions = sum(1 for p in positions if p.pnl < 0)

        return {
            "account_id": account_id,
            "total_capital": capital["total_capital"],
            "available_margin": capital["available_margin"],
            "total_position_value": total_position_value,
            "exposure_pct": exposure_pct,
            "total_unrealized_pnl": total_unrealized_pnl,
            "open_positions_count": len(positions),
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "win_rate": (winning_positions / len(positions) * 100) if positions else 0
        }
