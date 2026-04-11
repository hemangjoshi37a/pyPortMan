"""
Charts Module for pyPortMan
Generates chart data for dashboard visualization
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

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


class ChartsManager:
    """Manager for generating chart data for dashboard visualization"""

    def __init__(self, db: Session):
        self.db = db

    def get_equity_curve_data(
        self,
        account_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get equity curve data for charting
        Returns portfolio value over time

        Args:
            account_id: Optional account ID filter
            days: Number of days to look back

        Returns: {dates: [], total_values: [], day_pnl: [], day_pnl_pct: []}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.recorded_at >= cutoff_date
        )

        if account_id:
            query = query.filter(PortfolioSnapshot.account_id == account_id)

        snapshots = query.order_by(PortfolioSnapshot.recorded_at.asc()).all()

        dates = []
        total_values = []
        day_pnl = []
        day_pnl_pct = []

        for s in snapshots:
            dates.append(s.recorded_at.strftime("%Y-%m-%d %H:%M"))
            total_values.append(float(s.total_value))
            day_pnl.append(float(s.day_pnl))
            day_pnl_pct.append(float(s.day_pnl_percent))

        return {
            "dates": dates,
            "total_values": total_values,
            "day_pnl": day_pnl,
            "day_pnl_pct": day_pnl_pct,
            "account_id": account_id,
            "days": days
        }

    def get_pnl_distribution(
        self,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get P&L distribution data for charting
        Returns breakdown of P&L by stock

        Args:
            account_id: Optional account ID filter

        Returns: {stocks: [], pnl_values: [], pnl_percentages: [], categories: []}
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()

        stocks = []
        pnl_values = []
        pnl_percentages = []
        categories = []

        for h in holdings:
            stocks.append(h.stock)
            pnl_values.append(float(h.pnl))
            pnl_percentages.append(float(h.pnl_percent))
            categories.append "profit" if h.pnl >= 0 else "loss")

        return {
            "stocks": stocks,
            "pnl_values": pnl_values,
            "pnl_percentages": pnl_percentages,
            "categories": categories,
            "total_pnl": sum(pnl_values),
            "account_id": account_id
        }

    def get_sector_allocation(
        self,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get sector allocation data for pie chart
        Returns allocation by stock/sector

        Args:
            account_id: Optional account ID filter

        Returns: {labels: [], values: [], percentages: []}
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()

        # Group by stock
        allocation = {}
        for h in holdings:
            if h.stock not in allocation:
                allocation[h.stock] = 0
            allocation[h.stock] += h.current_value

        total_value = sum(allocation.values())

        labels = list(allocation.keys())
        values = [float(v) for v in allocation.values()]
        percentages = [(v / total_value * 100) if total_value > 0 else 0 for v in values]

        # Sort by value descending
        sorted_data = sorted(zip(labels, values, percentages), key=lambda x: x[1], reverse=True)
        labels, values, percentages = zip(*sorted_data) if sorted_data else ([], [], [])

        return {
            "labels": list(labels),
            "values": list(values),
            "percentages": list(percentages),
            "total_value": float(total_value),
            "account_id": account_id
        }

    def get_monthly_performance(
        self,
        account_id: Optional[int] = None,
        months: int = 12
    ) -> Dict[str, Any]:
        """
        Get monthly performance data for charting
        Returns P&L by month

        Args:
            account_id: Optional account ID filter
            months: Number of months to look back

        Returns: {months: [], pnl_values: [], pnl_percentages: []}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=months * 30)

        query = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.recorded_at >= cutoff_date
        )

        if account_id:
            query = query.filter(PortfolioSnapshot.account_id == account_id)

        snapshots = query.order_by(PortfolioSnapshot.recorded_at.asc()).all()

        # Group by month
        monthly_data = {}
        for s in snapshots:
            month_key = s.recorded_at.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {"pnl": 0, "value": 0}
            monthly_data[month_key]["pnl"] += s.day_pnl
            monthly_data[month_key]["value"] = s.total_value

        months_list = sorted(monthly_data.keys())
        pnl_values = [float(monthly_data[m]["pnl"]) for m in months_list]
        pnl_percentages = [
            (monthly_data[m]["pnl"] / monthly_data[m]["value"] * 100) if monthly_data[m]["value"] > 0 else 0
            for m in months_list
        ]

        return {
            "months": months_list,
            "pnl_values": pnl_values,
            "pnl_percentages": pnl_percentages,
            "account_id": account_id
        }

    def get_account_comparison(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get account comparison data for charting
        Returns portfolio values across all accounts

        Args:
            days: Number of days to look back

        Returns: {accounts: [], datasets: [{name, data: []}]}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        accounts = self.db.query(Account).filter(Account.is_active == True).all()

        datasets = []
        dates = []

        for account in accounts:
            snapshots = self.db.query(PortfolioSnapshot).filter(
                and_(
                    PortfolioSnapshot.account_id == account.id,
                    PortfolioSnapshot.recorded_at >= cutoff_date
                )
            ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

            if not dates and snapshots:
                dates = [s.recorded_at.strftime("%Y-%m-%d") for s in snapshots]

            data = [float(s.total_value) for s in snapshots]
            datasets.append({
                "name": account.name,
                "account_id": account.id,
                "data": data
            })

        return {
            "dates": dates,
            "datasets": datasets,
            "days": days
        }

    def get_top_performers(
        self,
        account_id: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get top performing stocks data for charting
        Returns best and worst performers

        Args:
            account_id: Optional account ID filter
            limit: Number of stocks to return

        Returns: {top_gainers: [], top_losers: []}
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()

        # Sort by P&L
        sorted_holdings = sorted(holdings, key=lambda h: h.pnl, reverse=True)

        top_gainers = []
        top_losers = []

        for h in sorted_holdings[:limit]:
            if h.pnl >= 0:
                top_gainers.append({
                    "stock": h.stock,
                    "pnl": float(h.pnl),
                    "pnl_percent": float(h.pnl_percent),
                    "current_value": float(h.current_value)
                })

        for h in sorted_holdings[-limit:]:
            if h.pnl < 0:
                top_losers.append({
                    "stock": h.stock,
                    "pnl": float(h.pnl),
                    "pnl_percent": float(h.pnl_percent),
                    "current_value": float(h.current_value)
                })

        return {
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "account_id": account_id
        }

    def get_exposure_over_time(
        self,
        account_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get exposure over time data for charting
        Returns how much capital is deployed over time

        Args:
            account_id: Optional account ID filter
            days: Number of days to look back

        Returns: {dates: [], exposure_values: [], exposure_percentages: []}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.recorded_at >= cutoff_date
        )

        if account_id:
            query = query.filter(PortfolioSnapshot.account_id == account_id)

        snapshots = query.order_by(PortfolioSnapshot.recorded_at.asc()).all()

        dates = []
        exposure_values = []
        exposure_percentages = []

        for s in snapshots:
            dates.append(s.recorded_at.strftime("%Y-%m-%d"))
            # Exposure = holdings value + positions value
            exposure = s.total_value
            exposure_values.append(float(exposure))
            exposure_percentages.append(100.0)  # Full exposure for now

        return {
            "dates": dates,
            "exposure_values": exposure_values,
            "exposure_percentages": exposure_percentages,
            "account_id": account_id
        }

    def get_win_loss_ratio(
        self,
        account_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get win/loss ratio data for charting
        Returns win vs loss counts over time

        Args:
            account_id: Optional account ID filter
            days: Number of days to look back

        Returns: {dates: [], wins: [], losses: [], win_rate: []}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get orders
        query = self.db.query(Order).filter(
            Order.placed_at >= cutoff_date
        )

        if account_id:
            query = query.filter(Order.account_id == account_id)

        orders = query.order_by(Order.placed_at.asc()).all()

        # Group by day
        daily_data = {}
        for order in orders:
            day_key = order.placed_at.strftime("%Y-%m-%d")
            if day_key not in daily_data:
                daily_data[day_key] = {"wins": 0, "losses": 0}

            # Simple win/loss based on status
            if order.status == "COMPLETE":
                daily_data[day_key]["wins"] += 1
            elif order.status in ["REJECTED", "CANCELLED"]:
                daily_data[day_key]["losses"] += 1

        dates = sorted(daily_data.keys())
        wins = [daily_data[d]["wins"] for d in dates]
        losses = [daily_data[d]["losses"] for d in dates]
        win_rate = [
            (daily_data[d]["wins"] / (daily_data[d]["wins"] + daily_data[d]["losses"]) * 100)
            if (daily_data[d]["wins"] + daily_data[d]["losses"]) > 0 else 0
            for d in dates
        ]

        return {
            "dates": dates,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "account_id": account_id
        }

    def get_dashboard_summary(
        self,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get complete dashboard summary with all chart data
        Returns combined data for dashboard

        Args:
            account_id: Optional account ID filter

        Returns: {equity_curve, pnl_distribution, sector_allocation, top_performers, ...}
        """
        return {
            "equity_curve": self.get_equity_curve_data(account_id),
            "pnl_distribution": self.get_pnl_distribution(account_id),
            "sector_allocation": self.get_sector_allocation(account_id),
            "monthly_performance": self.get_monthly_performance(account_id),
            "top_performers": self.get_top_performers(account_id),
            "exposure_over_time": self.get_exposure_over_time(account_id),
            "win_loss_ratio": self.get_win_loss_ratio(account_id),
            "account_comparison": self.get_account_comparison() if not account_id else None
        }
