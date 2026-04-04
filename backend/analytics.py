"""
Analytics Manager for pyPortMan Backend
Deep portfolio analysis with sector-wise breakdown, P&L analysis, risk metrics
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from models import Account, Holding, Position, PortfolioSnapshot, Order

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


class AnalyticsManager:
    """Manager for portfolio analytics and deep analysis"""

    def __init__(self, db: Session):
        self.db = db

    def get_portfolio_overview(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive portfolio overview

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with portfolio overview data
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()

        total_value = sum(h.current_value for h in holdings)
        investment_value = sum(h.qty * h.avg_price for h in holdings)
        total_pnl = sum(h.pnl for h in holdings)

        # Get positions P&L
        positions_query = self.db.query(Position)
        if account_id:
            positions_query = positions_query.filter(Position.account_id == account_id)
        positions = positions_query.all()
        positions_pnl = sum(p.pnl for p in positions)

        # Calculate metrics
        overall_pnl = total_pnl + positions_pnl
        overall_pnl_percent = (overall_pnl / investment_value * 100) if investment_value > 0 else 0

        # Get account count
        accounts_query = self.db.query(Account).filter(Account.is_active == True)
        if account_id:
            accounts_query = accounts_query.filter(Account.id == account_id)
        accounts_count = accounts_query.count()

        return {
            "total_value": total_value,
            "investment_value": investment_value,
            "total_pnl": total_pnl,
            "positions_pnl": positions_pnl,
            "overall_pnl": overall_pnl,
            "overall_pnl_percent": overall_pnl_percent,
            "holdings_count": len(holdings),
            "positions_count": len(positions),
            "accounts_count": accounts_count,
            "as_of": datetime.utcnow().isoformat()
        }

    def get_stock_allocation(self, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get stock-wise allocation breakdown

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            List of stocks with allocation data
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()
        total_value = sum(h.current_value for h in holdings)

        allocation = []
        for h in holdings:
            value = h.current_value
            percentage = (value / total_value * 100) if total_value > 0 else 0

            allocation.append({
                "stock": h.stock,
                "exchange": h.exchange,
                "value": value,
                "percentage": percentage,
                "qty": h.qty,
                "avg_price": h.avg_price,
                "ltp": h.ltp,
                "pnl": h.pnl,
                "pnl_percent": h.pnl_percent
            })

        # Sort by percentage descending
        allocation.sort(key=lambda x: x["percentage"], reverse=True)

        return allocation

    def get_pnl_breakdown(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detailed P&L breakdown

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with P&L breakdown data
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()

        # Categorize by P&L
        gainers = [h for h in holdings if h.pnl > 0]
        losers = [h for h in holdings if h.pnl < 0]
        neutral = [h for h in holdings if h.pnl == 0]

        total_gains = sum(h.pnl for h in gainers)
        total_losses = sum(h.pnl for h in losers)

        # Top gainers and losers
        top_gainers = sorted(gainers, key=lambda x: x.pnl, reverse=True)[:5]
        top_losers = sorted(losers, key=lambda x: x.pnl)[:5]

        return {
            "total_gains": total_gains,
            "total_losses": total_losses,
            "net_pnl": total_gains + total_losses,
            "gainers_count": len(gainers),
            "losers_count": len(losers),
            "neutral_count": len(neutral),
            "top_gainers": [
                {
                    "stock": h.stock,
                    "pnl": h.pnl,
                    "pnl_percent": h.pnl_percent,
                    "current_value": h.current_value
                }
                for h in top_gainers
            ],
            "top_losers": [
                {
                    "stock": h.stock,
                    "pnl": h.pnl,
                    "pnl_percent": h.pnl_percent,
                    "current_value": h.current_value
                }
                for h in top_losers
            ]
        }

    def get_risk_metrics(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate risk metrics for the portfolio

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with risk metrics
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()

        if not holdings:
            return {
                "concentration_risk": 0,
                "max_single_stock_exposure": 0,
                "diversification_score": 0,
                "loss_making_stocks": 0,
                "loss_making_percentage": 0
            }

        total_value = sum(h.current_value for h in holdings)

        # Concentration risk (max single stock exposure)
        max_single_stock = max(h.current_value for h in holdings)
        concentration_risk = (max_single_stock / total_value * 100) if total_value > 0 else 0

        # Diversification score (inverse of concentration)
        diversification_score = 100 - concentration_risk

        # Loss-making stocks
        loss_making = [h for h in holdings if h.pnl < 0]
        loss_making_percentage = (len(loss_making) / len(holdings) * 100) if holdings else 0

        return {
            "concentration_risk": round(concentration_risk, 2),
            "max_single_stock_exposure": round(max_single_stock, 2),
            "diversification_score": round(diversification_score, 2),
            "loss_making_stocks": len(loss_making),
            "loss_making_percentage": round(loss_making_percentage, 2),
            "total_stocks": len(holdings)
        }

    def get_equity_curve(self, days: int = 30, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get equity curve data for charting

        Args:
            days: Number of days to include
            account_id: Filter by account ID (optional)

        Returns:
            List of data points for equity curve
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.recorded_at >= cutoff_date
        )

        if account_id:
            query = query.filter(PortfolioSnapshot.account_id == account_id)

        snapshots = query.order_by(PortfolioSnapshot.recorded_at.asc()).all()

        return [
            {
                "date": s.recorded_at.isoformat(),
                "total_value": s.total_value,
                "investment_value": s.investment_value,
                "day_pnl": s.day_pnl,
                "day_pnl_percent": s.day_pnl_percent,
                "overall_pnl": s.overall_pnl,
                "overall_pnl_percent": s.overall_pnl_percent
            }
            for s in snapshots
        ]

    def get_account_comparison(self) -> List[Dict[str, Any]]:
        """
        Get comparison data across all accounts

        Returns:
            List of account comparison data
        """
        accounts = self.db.query(Account).filter(Account.is_active == True).all()

        comparison = []
        for account in accounts:
            holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
            positions = self.db.query(Position).filter(Position.account_id == account.id).all()

            total_value = sum(h.current_value for h in holdings)
            investment_value = sum(h.qty * h.avg_price for h in holdings)
            total_pnl = sum(h.pnl for h in holdings) + sum(p.pnl for p in positions)

            comparison.append({
                "account_id": account.id,
                "account_name": account.name,
                "total_value": total_value,
                "investment_value": investment_value,
                "pnl": total_pnl,
                "pnl_percent": (total_pnl / investment_value * 100) if investment_value > 0 else 0,
                "holdings_count": len(holdings),
                "positions_count": len(positions)
            })

        # Sort by total value descending
        comparison.sort(key=lambda x: x["total_value"], reverse=True)

        return comparison

    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get performance summary over a period

        Args:
            days: Number of days to analyze

        Returns:
            Dict with performance summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get snapshots for the period
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.recorded_at >= cutoff_date
        ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

        if not snapshots:
            return {
                "period_days": days,
                "start_value": 0,
                "end_value": 0,
                "period_return": 0,
                "period_return_percent": 0,
                "best_day": None,
                "worst_day": None
            }

        start_value = snapshots[0].total_value
        end_value = snapshots[-1].total_value
        period_return = end_value - start_value
        period_return_percent = (period_return / start_value * 100) if start_value > 0 else 0

        # Find best and worst days
        best_day = max(snapshots, key=lambda s: s.day_pnl)
        worst_day = min(snapshots, key=lambda s: s.day_pnl)

        return {
            "period_days": days,
            "start_value": start_value,
            "end_value": end_value,
            "period_return": period_return,
            "period_return_percent": period_return_percent,
            "best_day": {
                "date": best_day.recorded_at.isoformat(),
                "pnl": best_day.day_pnl,
                "pnl_percent": best_day.day_pnl_percent
            },
            "worst_day": {
                "date": worst_day.recorded_at.isoformat(),
                "pnl": worst_day.day_pnl,
                "pnl_percent": worst_day.day_pnl_percent
            }
        }

    def get_sector_analysis(self) -> Dict[str, Any]:
        """
        Get sector-wise analysis (simplified - based on stock patterns)

        Returns:
            Dict with sector analysis
        """
        holdings = self.db.query(Holding).all()

        # Simple sector classification based on stock patterns
        # In production, this would use a proper sector mapping
        sector_mapping = {
            "RELIANCE": "Energy",
            "TCS": "IT",
            "INFY": "IT",
            "HDFCBANK": "Banking",
            "ICICIBANK": "Banking",
            "SBIN": "Banking",
            "HINDUNILVR": "FMCG",
            "ITC": "FMCG",
            "TATAMOTORS": "Auto",
            "MARUTI": "Auto",
            "BAJFINANCE": "Finance",
            "AXISBANK": "Banking",
            "KOTAKBANK": "Banking",
            "LT": "Infrastructure",
            "WIPRO": "IT",
            "TECHM": "IT",
        }

        sector_data = {}
        total_value = sum(h.current_value for h in holdings)

        for h in holdings:
            sector = sector_mapping.get(h.stock, "Others")

            if sector not in sector_data:
                sector_data[sector] = {
                    "value": 0,
                    "count": 0,
                    "pnl": 0
                }

            sector_data[sector]["value"] += h.current_value
            sector_data[sector]["count"] += 1
            sector_data[sector]["pnl"] += h.pnl

        # Convert to list and calculate percentages
        sectors = []
        for sector, data in sector_data.items():
            sectors.append({
                "sector": sector,
                "value": data["value"],
                "percentage": (data["value"] / total_value * 100) if total_value > 0 else 0,
                "count": data["count"],
                "pnl": data["pnl"]
            })

        # Sort by value descending
        sectors.sort(key=lambda x: x["value"], reverse=True)

        return {
            "sectors": sectors,
            "total_value": total_value
        }

    def get_trading_activity(self, days: int = 30) -> Dict[str, Any]:
        """
        Get trading activity summary

        Args:
            days: Number of days to analyze

        Returns:
            Dict with trading activity data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        orders = self.db.query(Order).filter(
            Order.placed_at >= cutoff_date
        ).all()

        # Count by type
        buy_orders = [o for o in orders if o.transaction_type == "BUY"]
        sell_orders = [o for o in orders if o.transaction_type == "SELL"]

        # Count by status
        completed_orders = [o for o in orders if o.status == "COMPLETE"]
        rejected_orders = [o for o in orders if o.status == "REJECTED"]
        cancelled_orders = [o for o in orders if o.status == "CANCELLED"]

        # Calculate turnover
        buy_turnover = sum(o.price * o.qty for o in buy_orders)
        sell_turnover = sum(o.price * o.qty for o in sell_orders)
        total_turnover = buy_turnover + sell_turnover

        return {
            "period_days": days,
            "total_orders": len(orders),
            "buy_orders": len(buy_orders),
            "sell_orders": len(sell_orders),
            "completed_orders": len(completed_orders),
            "rejected_orders": len(rejected_orders),
            "cancelled_orders": len(cancelled_orders),
            "buy_turnover": buy_turnover,
            "sell_turnover": sell_turnover,
            "total_turnover": total_turnover
        }


if __name__ == "__main__":
    # Test analytics
    from database import SessionLocal

    db = SessionLocal()
    manager = AnalyticsManager(db)

    # Test portfolio overview
    overview = manager.get_portfolio_overview()
    print(f"Portfolio Overview: {overview}")

    # Test stock allocation
    allocation = manager.get_stock_allocation()
    print(f"Stock Allocation: {len(allocation)} stocks")

    # Test P&L breakdown
    pnl_breakdown = manager.get_pnl_breakdown()
    print(f"P&L Breakdown: {pnl_breakdown}")

    # Test risk metrics
    risk = manager.get_risk_metrics()
    print(f"Risk Metrics: {risk}")

    db.close()
