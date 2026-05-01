"""
Trading Statistics Manager for pyPortMan
Track win rate and risk-reward analysis over time
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import numpy as np

from models import Account, Order, TradingStatistics, PortfolioSnapshot

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


class TradingStatisticsManager:
    """Manager for trading statistics and performance analysis"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_statistics(
        self,
        account_id: int,
        period: str = "DAILY"
    ) -> TradingStatistics:
        """
        Calculate trading statistics for a given period
        period: DAILY, WEEKLY, MONTHLY, YEARLY, ALL_TIME
        """
        # Determine date range
        now = datetime.utcnow()
        if period == "DAILY":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "WEEKLY":
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "MONTHLY":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "YEARLY":
            period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # ALL_TIME
            period_start = datetime.min

        period_end = now

        # Get completed orders in the period
        orders = self.db.query(Order).filter(
            Order.account_id == account_id,
            Order.placed_at >= period_start,
            Order.placed_at <= period_end,
            Order.status == "COMPLETE"
        ).all()

        # Calculate statistics
        total_trades = len(orders)
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0

        total_profit = 0
        total_loss = 0
        profits = []
        losses = []

        for order in orders:
            # Simplified P&L calculation (in production, use actual trade data)
            pnl = 0  # This would be calculated from actual trade data

            if pnl > 0:
                winning_trades += 1
                total_profit += pnl
                profits.append(pnl)
            elif pnl < 0:
                losing_trades += 1
                total_loss += abs(pnl)
                losses.append(abs(pnl))
            else:
                break_even_trades += 1

        # Calculate win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        loss_rate = (losing_trades / total_trades * 100) if total_trades > 0 else 0

        # Calculate averages
        avg_profit = (total_profit / winning_trades) if winning_trades > 0 else 0
        avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0

        # Calculate risk-reward ratio
        risk_reward_ratio = (avg_profit / avg_loss) if avg_loss > 0 else 0

        # Calculate max profit and loss
        max_profit = max(profits) if profits else 0
        max_loss = max(losses) if losses else 0

        # Calculate total P&L
        total_pnl = total_profit - total_loss

        # Calculate drawdown from portfolio snapshots
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= period_start,
            PortfolioSnapshot.recorded_at <= period_end
        ).all()

        max_drawdown = 0
        max_drawdown_pct = 0

        if snapshots:
            peak_value = max(s.total_value for s in snapshots)
            for snapshot in snapshots:
                drawdown = peak_value - snapshot.total_value
                drawdown_pct = (drawdown / peak_value * 100) if peak_value > 0 else 0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_pct = drawdown_pct

        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = None
        sortino_ratio = None

        if len(profits) > 1 and len(losses) > 1:
            returns = profits + [-l for l in losses]
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0

                # Sortino ratio (only downside deviation)
                downside_returns = [r for r in returns if r < 0]
                if downside_returns:
                    downside_std = np.std(downside_returns)
                    sortino_ratio = (avg_return / downside_std) if downside_std > 0 else 0

        # Create or update statistics record
        stats = self.db.query(TradingStatistics).filter(
            TradingStatistics.account_id == account_id,
            TradingStatistics.period == period,
            TradingStatistics.period_start == period_start
        ).first()

        if not stats:
            stats = TradingStatistics(
                account_id=account_id,
                period=period,
                period_start=period_start,
                period_end=period_end
            )
            self.db.add(stats)

        # Update statistics
        stats.total_trades = total_trades
        stats.winning_trades = winning_trades
        stats.losing_trades = losing_trades
        stats.break_even_trades = break_even_trades
        stats.win_rate = win_rate
        stats.loss_rate = loss_rate
        stats.total_pnl = total_pnl
        stats.total_profit = total_profit
        stats.total_loss = total_loss
        stats.avg_profit = avg_profit
        stats.avg_loss = avg_loss
        stats.risk_reward_ratio = risk_reward_ratio
        stats.max_profit = max_profit
        stats.max_loss = max_loss
        stats.max_drawdown = max_drawdown
        stats.max_drawdown_pct = max_drawdown_pct
        stats.sharpe_ratio = sharpe_ratio
        stats.sortino_ratio = sortino_ratio
        stats.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(stats)

        logger.info(f"Calculated {period} statistics for account {account_id}")
        return stats

    def get_statistics(
        self,
        account_id: int,
        period: Optional[str] = None
    ) -> List[TradingStatistics]:
        """
        Get trading statistics with optional period filter
        """
        query = self.db.query(TradingStatistics).filter(
            TradingStatistics.account_id == account_id
        )

        if period:
            query = query.filter(TradingStatistics.period == period)

        return query.order_by(TradingStatistics.period_start.desc()).all()

    def get_statistics_summary(self, account_id: int) -> Dict[str, Any]:
        """
        Get summary of trading statistics across all periods
        """
        all_stats = self.get_statistics(account_id)

        if not all_stats:
            return {
                "message": "No statistics available",
                "periods": []
            }

        # Group by period
        period_stats = {}
        for stat in all_stats:
            if stat.period not in period_stats:
                period_stats[stat.period] = []
            period_stats[stat.period].append(stat)

        # Get latest for each period
        latest_stats = {}
        for period, stats_list in period_stats.items():
            latest_stats[period] = max(stats_list, key=lambda s: s.period_start)

        return {
            "periods": list(latest_stats.keys()),
            "statistics": {
                period: {
                    "total_trades": stat.total_trades,
                    "win_rate": stat.win_rate,
                    "risk_reward_ratio": stat.risk_reward_ratio,
                    "total_pnl": stat.total_pnl,
                    "max_drawdown_pct": stat.max_drawdown_pct,
                    "sharpe_ratio": stat.sharpe_ratio,
                    "sortino_ratio": stat.sortino_ratio
                }
                for period, stat in latest_stats.items()
            }
        }

    def get_win_rate_trend(
        self,
        account_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get win rate trend over time
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        stats = self.db.query(TradingStatistics).filter(
            TradingStatistics.account_id == account_id,
            TradingStatistics.period_start >= cutoff
        ).order_by(
            TradingStatistics.period_start.asc()
        ).all()

        trend = []
        for stat in stats:
            trend.append({
                "date": stat.period_start.isoformat(),
                "win_rate": stat.win_rate,
                "total_trades": stat.total_trades,
                "winning_trades": stat.winning_trades,
                "losing_trades": stat.losing_trades
            })

        return trend

    def get_risk_reward_analysis(self, account_id: int) -> Dict[str, Any]:
        """
        Get detailed risk-reward analysis
        """
        all_time_stats = self.calculate_statistics(account_id, "ALL_TIME")

        return {
            "risk_reward_ratio": all_time_stats.risk_reward_ratio,
            "avg_profit": all_time_stats.avg_profit,
            "avg_loss": all_time_stats.avg_loss,
            "max_profit": all_time_stats.max_profit,
            "max_loss": all_time_stats.max_loss,
            "profit_factor": (all_time_stats.total_profit / all_time_stats.total_loss) if all_time_stats.total_loss > 0 else 0,
            "win_rate": all_time_stats.win_rate,
            "loss_rate": all_time_stats.loss_rate,
            "total_trades": all_time_stats.total_trades,
            "winning_trades": all_time_stats.winning_trades,
            "losing_trades": all_time_stats.losing_trades
        }

    def get_performance_metrics(self, account_id: int) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics
        """
        daily_stats = self.calculate_statistics(account_id, "DAILY")
        weekly_stats = self.calculate_statistics(account_id, "WEEKLY")
        monthly_stats = self.calculate_statistics(account_id, "MONTHLY")
        all_time_stats = self.calculate_statistics(account_id, "ALL_TIME")

        return {
            "daily": {
                "win_rate": daily_stats.win_rate,
                "total_pnl": daily_stats.total_pnl,
                "total_trades": daily_stats.total_trades
            },
            "weekly": {
                "win_rate": weekly_stats.win_rate,
                "total_pnl": weekly_stats.total_pnl,
                "total_trades": weekly_stats.total_trades
            },
            "monthly": {
                "win_rate": monthly_stats.win_rate,
                "total_pnl": monthly_stats.total_pnl,
                "total_trades": monthly_stats.total_trades
            },
            "all_time": {
                "win_rate": all_time_stats.win_rate,
                "total_pnl": all_time_stats.total_pnl,
                "total_trades": all_time_stats.total_trades,
                "risk_reward_ratio": all_time_stats.risk_reward_ratio,
                "sharpe_ratio": all_time_stats.sharpe_ratio,
                "sortino_ratio": all_time_stats.sortino_ratio,
                "max_drawdown_pct": all_time_stats.max_drawdown_pct
            }
        }

    def get_trade_distribution(self, account_id: int) -> Dict[str, Any]:
        """
        Get distribution of trades by outcome
        """
        all_time_stats = self.calculate_statistics(account_id, "ALL_TIME")

        total = all_time_stats.total_trades
        if total == 0:
            return {"message": "No trades recorded"}

        return {
            "total_trades": total,
            "winning_trades": all_time_stats.winning_trades,
            "losing_trades": all_time_stats.losing_trades,
            "break_even_trades": all_time_stats.break_even_trades,
            "win_rate_pct": all_time_stats.win_rate,
            "loss_rate_pct": all_time_stats.loss_rate,
            "break_even_rate_pct": (all_time_stats.break_even_trades / total * 100)
        }
