"""
Analytics Manager for pyPortMan Backend
Deep portfolio analysis with sector-wise breakdown, P&L analysis, risk metrics
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from models import Account, Holding, Position, PortfolioSnapshot, Order, GTTOrder

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

    def get_comprehensive_portfolio_analysis(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Comprehensive portfolio analysis with advanced metrics

        Calculates:
        - Risk metrics: Sharpe ratio, Sortino ratio, Maximum Drawdown, VaR
        - Efficiency metrics: Information ratio, Beta, Alpha
        - Diversification: HHI index, sector concentration
        - Performance: Win rate, Average win/loss, Profit factor
        - Portfolio health score

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with comprehensive portfolio analysis
        """
        # Get holdings and positions
        holdings_query = self.db.query(Holding)
        if account_id:
            holdings_query = holdings_query.filter(Holding.account_id == account_id)
        holdings = holdings_query.all()

        positions_query = self.db.query(Position)
        if account_id:
            positions_query = positions_query.filter(Position.account_id == account_id)
        positions = positions_query.all()

        # Get historical data for advanced metrics
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.recorded_at >= cutoff_date
        )
        if account_id:
            snapshots = snapshots.filter(PortfolioSnapshot.account_id == account_id)
        snapshots = snapshots.order_by(PortfolioSnapshot.recorded_t.asc()).all()

        # Basic portfolio values
        total_value = sum(h.current_value for h in holdings)
        investment_value = sum(h.qty * h.avg_price for h in holdings)
        total_pnl = sum(h.pnl for h in holdings) + sum(p.pnl for p in positions)

        # ==================== RISK METRICS ====================

        # Calculate daily returns from snapshots
        daily_returns = []
        for i in range(1, len(snapshots)):
            if snapshots[i - 1].total_value > 0:
                daily_return = (snapshots[i].total_value - snapshots[i - 1].total_value) / snapshots[i - 1].total_value
                daily_returns.append(daily_return)

        # Sharpe Ratio (assuming 252 trading days, risk-free rate of 6%)
        risk_free_rate = 0.06 / 252  # Daily risk-free rate
        sharpe_ratio = 0
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            std_dev = (sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
            sharpe_ratio = ((avg_return - risk_free_rate) / std_dev) * (252 ** 0.5) if std_dev > 0 else 0

        # Sortino Ratio (downside deviation)
        sortino_ratio = 0
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            downside_returns = [r for r in daily_returns if r < 0]
            downside_dev = (sum(r ** 2 for r in downside_returns) / len(downside_returns)) ** 0.5 if downside_returns else 0
            sortino_ratio = ((avg_return - risk_free_rate) / downside_dev) * (252 ** 0.5) if downside_dev > 0 else 0

        # Maximum Drawdown
        max_drawdown = 0
        max_drawdown_date = None
        peak_value = 0
        for s in snapshots:
            if s.total_value > peak_value:
                peak_value = s.total_value
            drawdown = (peak_value - s.total_value) / peak_value if peak_value > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_date = s.recorded_at.isoformat()

        # Value at Risk (VaR) - 95% confidence
        var_95 = 0
        if daily_returns:
            sorted_returns = sorted(daily_returns)
            var_index = int(len(sorted_returns) * 0.05)
            var_95 = abs(sorted_returns[var_index]) if var_index < len(sorted_returns) else 0

        # ==================== EFFICIENCY METRICS ====================

        # Information Ratio (tracking error against benchmark)
        # Using NIFTY 50 as proxy benchmark (assuming 12% annual return)
        benchmark_return = 0.12 / 252
        tracking_error = 0
        information_ratio = 0
        if daily_returns:
            excess_returns = [r - benchmark_return for r in daily_returns]
            avg_excess = sum(excess_returns) / len(excess_returns)
            tracking_error = (sum((er - avg_excess) ** 2 for er in excess_returns) / len(excess_returns)) ** 0.5
            information_ratio = (avg_excess / tracking_error) * (252 ** 0.5) if tracking_error > 0 else 0

        # Beta (sensitivity to market)
        beta = 1.0  # Default to 1.0
        alpha = 0
        if len(daily_returns) > 30:
            # Calculate covariance with market (simplified)
            market_returns = [benchmark_return] * len(daily_returns)
            avg_portfolio = sum(daily_returns) / len(daily_returns)
            avg_market = sum(market_returns) / len(market_returns)

            covariance = sum((d - avg_portfolio) * (m - avg_market) for d, m in zip(daily_returns, market_returns)) / len(daily_returns)
            market_variance = sum((m - avg_market) ** 2 for m in market_returns) / len(market_returns)

            beta = covariance / market_variance if market_variance > 0 else 1.0
            alpha = (avg_portfolio - risk_free_rate) - beta * (benchmark_return - risk_free_rate)

        # ==================== DIVERSIFICATION METRICS ====================

        # Herfindahl-Hirschman Index (HHI) for concentration
        hhi = 0
        if total_value > 0 and holdings:
            for h in holdings:
                weight = h.current_value / total_value
                hhi += weight ** 2
            hhi *= 10000  # Scale to 0-10000 range

        # Effective number of stocks (inverse of HHI)
        effective_stocks = 1 / hhi * 10000 if hhi > 0 else 0

        # Sector concentration
        sector_mapping = {
            "RELIANCE": "Energy", "TCS": "IT", "INFY": "IT", "HDFCBANK": "Banking",
            "ICICIBANK": "Banking", "SBIN": "Banking", "HINDUNILVR": "FMCG",
            "ITC": "FMCG", "TATAMOTORS": "Auto", "MARUTI": "Auto",
            "BAJFINANCE": "Finance", "AXISBANK": "Banking", "KOTAKBANK": "Banking",
            "LT": "Infrastructure", "WIPRO": "IT", "TECHM": "IT",
        }

        sector_weights = {}
        for h in holdings:
            sector = sector_mapping.get(h.stock, "Others")
            if sector not in sector_weights:
                sector_weights[sector] = 0
            sector_weights[sector] += h.current_value / total_value if total_value > 0 else 0

        sector_hhi = sum(w ** 2 for w in sector_weights.values()) * 10000

        # ==================== PERFORMANCE METRICS ====================

        # Win/Loss analysis
        gainers = [h for h in holdings if h.pnl > 0]
        losers = [h for h in holdings if h.pnl < 0]

        win_rate = len(gainers) / len(holdings) * 100 if holdings else 0

        avg_win = sum(h.pnl for h in gainers) / len(gainers) if gainers else 0
        avg_loss = sum(h.pnl for h in losers) / len(losers) if losers else 0

        # Profit Factor
        total_gains = sum(h.pnl for h in gainers)
        total_losses = abs(sum(h.pnl for h in losers))
        profit_factor = total_gains / total_losses if total_losses > 0 else float('inf') if total_gains > 0 else 0

        # ==================== PORTFOLIO HEALTH SCORE ====================

        # Calculate health score (0-100)
        health_components = {
            "diversification": min(100, effective_stocks * 10),  # More stocks = better
            "risk_adjusted_return": min(100, (sharpe_ratio + 1) * 50),  # Sharpe > 0 is good
            "drawdown_control": max(0, 100 - max_drawdown * 100),  # Lower drawdown = better
            "win_rate": win_rate,
            "profit_factor": min(100, profit_factor * 20)  # PF > 2 is excellent
        }

        health_score = sum(health_components.values()) / len(health_components)

        # ==================== RECOMMENDATIONS ====================

        recommendations = []
        if hhi > 2500:
            recommendations.append({
                "type": "warning",
                "message": f"High concentration risk detected (HHI: {hhi:.0f}). Consider diversifying across more stocks."
            })
        if max_drawdown > 0.20:
            recommendations.append({
                "type": "warning",
                "message": f"Maximum drawdown of {max_drawdown*100:.1f}% is high. Review risk management strategy."
            })
        if win_rate < 40:
            recommendations.append({
                "type": "info",
                "message": f"Win rate is {win_rate:.1f}%. Consider reviewing entry/exit criteria."
            })
        if profit_factor < 1:
            recommendations.append({
                "type": "warning",
                "message": f"Profit factor is {profit_factor:.2f}. Losses exceed gains - review position sizing."
            })
        if sharpe_ratio < 0.5:
            recommendations.append({
                "type": "info",
                "message": f"Sharpe ratio is {sharpe_ratio:.2f}. Consider improving risk-adjusted returns."
            })
        if not recommendations:
            recommendations.append({
                "type": "success",
                "message": "Portfolio metrics look healthy!"
            })

        return {
            "summary": {
                "total_value": total_value,
                "investment_value": investment_value,
                "total_pnl": total_pnl,
                "pnl_percent": (total_pnl / investment_value * 100) if investment_value > 0 else 0,
                "holdings_count": len(holdings),
                "positions_count": len(positions),
                "health_score": round(health_score, 1),
                "health_rating": self._get_health_rating(health_score)
            },
            "risk_metrics": {
                "sharpe_ratio": round(sharpe_ratio, 3),
                "sortino_ratio": round(sortino_ratio, 3),
                "max_drawdown": round(max_drawdown * 100, 2),
                "max_drawdown_date": max_drawdown_date,
                "var_95": round(var_95 * 100, 2),
                "beta": round(beta, 2),
                "tracking_error": round(tracking_error * (252 ** 0.5), 3)
            },
            "efficiency_metrics": {
                "information_ratio": round(information_ratio, 3),
                "alpha": round(alpha * 252 * 100, 2),  # Annualized alpha in %
                "beta": round(beta, 2)
            },
            "diversification": {
                "hhi": round(hhi, 0),
                "effective_stocks": round(effective_stocks, 1),
                "sector_hhi": round(sector_hhi, 0),
                "sector_breakdown": [
                    {"sector": s, "weight": round(w * 100, 2)}
                    for s, w in sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)
                ]
            },
            "performance": {
                "win_rate": round(win_rate, 1),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2),
                "gainers_count": len(gainers),
                "losers_count": len(losers)
            },
            "health_components": {k: round(v, 1) for k, v in health_components.items()},
            "recommendations": recommendations,
            "analysis_date": datetime.utcnow().isoformat()
        }

    def _get_health_rating(self, score: float) -> str:
        """Get health rating based on score"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Poor"

    def get_risk_reward_ratios(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate risk-reward ratios for portfolio positions

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with risk-reward ratio analysis
        """
        # Get holdings
        holdings_query = self.db.query(Holding)
        if account_id:
            holdings_query = holdings_query.filter(Holding.account_id == account_id)
        holdings = holdings_query.all()

        # Get positions
        positions_query = self.db.query(Position)
        if account_id:
            positions_query = positions_query.filter(Position.account_id == account_id)
        positions = positions_query.all()

        # Get GTT orders for target/stop-loss information
        gtt_query = self.db.query(GTTOrder)
        if account_id:
            gtt_query = gtt_query.filter(GTTOrder.account_id == account_id)
        gtt_orders = gtt_query.filter(GTTOrder.status == "ACTIVE").all()

        # Create a mapping of stock to GTT target/stop-loss
        gtt_mapping = {}
        for gtt in gtt_orders:
            gtt_mapping[gtt.stock] = {
                "target_price": gtt.target_price,
                "sl_price": gtt.sl_price,
                "buy_price": gtt.buy_price
            }

        # Calculate per-position risk-reward ratios
        position_rr = []
        total_risk = 0
        total_reward = 0

        for h in holdings:
            current_price = h.ltp
            entry_price = h.avg_price

            # Get target and stop-loss from GTT or use defaults
            gtt_info = gtt_mapping.get(h.stock, {})
            target_price = gtt_info.get("target_price", entry_price * 1.1)  # Default 10% target
            sl_price = gtt_info.get("sl_price", entry_price * 0.95)  # Default 5% stop-loss

            # Calculate risk and reward
            risk_amount = (entry_price - sl_price) * h.qty if sl_price < entry_price else 0
            reward_amount = (target_price - entry_price) * h.qty if target_price > entry_price else 0

            # Risk-reward ratio
            rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

            # Current unrealized P&L
            unrealized_pnl = h.pnl

            position_rr.append({
                "stock": h.stock,
                "exchange": h.exchange,
                "entry_price": round(entry_price, 2),
                "current_price": round(current_price, 2),
                "target_price": round(target_price, 2),
                "stop_loss": round(sl_price, 2),
                "quantity": h.qty,
                "risk_amount": round(risk_amount, 2),
                "reward_amount": round(reward_amount, 2),
                "risk_reward_ratio": round(rr_ratio, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "pnl_percent": round(h.pnl_percent, 2),
                "distance_to_target_pct": round(((target_price - current_price) / current_price * 100), 2) if current_price > 0 else 0,
                "distance_to_sl_pct": round(((current_price - sl_price) / current_price * 100), 2) if current_price > 0 else 0
            })

            total_risk += risk_amount
            total_reward += reward_amount

        # Calculate for positions (intraday)
        for p in positions:
            current_price = p.ltp
            entry_price = p.avg_price

            # For positions, use a default 2% stop-loss and 4% target
            target_price = entry_price * 1.04
            sl_price = entry_price * 0.98

            risk_amount = (entry_price - sl_price) * abs(p.qty) if sl_price < entry_price else 0
            reward_amount = (target_price - entry_price) * abs(p.qty) if target_price > entry_price else 0
            rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

            position_rr.append({
                "stock": p.stock,
                "exchange": p.exchange,
                "entry_price": round(entry_price, 2),
                "current_price": round(current_price, 2),
                "target_price": round(target_price, 2),
                "stop_loss": round(sl_price, 2),
                "quantity": abs(p.qty),
                "risk_amount": round(risk_amount, 2),
                "reward_amount": round(reward_amount, 2),
                "risk_reward_ratio": round(rr_ratio, 2),
                "unrealized_pnl": round(p.unrealized_pnl, 2),
                "pnl_percent": round(p.pnl_percent, 2),
                "distance_to_target_pct": round(((target_price - current_price) / current_price * 100), 2) if current_price > 0 else 0,
                "distance_to_sl_pct": round(((current_price - sl_price) / current_price * 100), 2) if current_price > 0 else 0,
                "is_position": True
            })

            total_risk += risk_amount
            total_reward += reward_amount

        # Portfolio-level risk-reward
        portfolio_rr = total_reward / total_risk if total_risk > 0 else 0

        # Categorize positions by risk-reward quality
        excellent_rr = [p for p in position_rr if p["risk_reward_ratio"] >= 2.0]
        good_rr = [p for p in position_rr if 1.5 <= p["risk_reward_ratio"] < 2.0]
        fair_rr = [p for p in position_rr if 1.0 <= p["risk_reward_ratio"] < 1.5]
        poor_rr = [p for p in position_rr if p["risk_reward_ratio"] < 1.0]

        return {
            "portfolio_risk_reward_ratio": round(portfolio_rr, 2),
            "total_risk_amount": round(total_risk, 2),
            "total_reward_amount": round(total_reward, 2),
            "positions_count": len(position_rr),
            "positions": position_rr,
            "summary": {
                "excellent_rr_count": len(excellent_rr),
                "good_rr_count": len(good_rr),
                "fair_rr_count": len(fair_rr),
                "poor_rr_count": len(poor_rr),
                "avg_rr_ratio": round(sum(p["risk_reward_ratio"] for p in position_rr) / len(position_rr), 2) if position_rr else 0
            },
            "recommendations": self._get_rr_recommendations(portfolio_rr, position_rr)
        }

    def _get_rr_recommendations(self, portfolio_rr: float, positions: List[Dict]) -> List[Dict[str, Any]]:
        """Get recommendations based on risk-reward analysis"""
        recommendations = []

        if portfolio_rr < 1.0:
            recommendations.append({
                "type": "warning",
                "message": f"Portfolio risk-reward ratio ({portfolio_rr:.2f}) is below 1.0. Consider adjusting stop-loss levels or target prices."
            })
        elif portfolio_rr < 1.5:
            recommendations.append({
                "type": "info",
                "message": f"Portfolio risk-reward ratio ({portfolio_rr:.2f}) is moderate. Aim for ratio above 2.0 for better risk-adjusted returns."
            })

        poor_positions = [p for p in positions if p["risk_reward_ratio"] < 1.0]
        if poor_positions:
            stocks = ", ".join([p["stock"] for p in poor_positions[:3]])
            recommendations.append({
                "type": "warning",
                "message": f"{len(poor_positions)} positions have poor risk-reward ratios (< 1.0): {stocks}{'...' if len(poor_positions) > 3 else ''}"
            })

        near_sl_positions = [p for p in positions if p["distance_to_sl_pct"] < 2]
        if near_sl_positions:
            stocks = ", ".join([p["stock"] for p in near_sl_positions[:3]])
            recommendations.append({
                "type": "urgent",
                "message": f"{len(near_sl_positions)} positions are within 2% of stop-loss: {stocks}{'...' if len(near_sl_positions) > 3 else ''}"
            })

        return recommendations

    def get_portfolio_correlation_matrix(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate correlation matrix for portfolio holdings

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with correlation matrix data
        """
        holdings_query = self.db.query(Holding)
        if account_id:
            holdings_query = holdings_query.filter(Holding.account_id == account_id)
        holdings = holdings_query.all()

        if len(holdings) < 2:
            return {
                "message": "Need at least 2 holdings for correlation analysis",
                "matrix": []
            }

        # Get historical returns for each stock
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        stock_returns = {}

        for h in holdings:
            # Get snapshots for this stock (simplified - using portfolio snapshots)
            # In production, you'd have individual stock price history
            stock_returns[h.stock] = []

        # For now, return a placeholder correlation matrix
        # In production, this would calculate actual correlations from price history
        stocks = [h.stock for h in holdings]
        matrix = []

        for i, stock1 in enumerate(stocks):
            row = {"stock": stock1, "correlations": []}
            for j, stock2 in enumerate(stocks):
                if i == j:
                    correlation = 1.0
                else:
                    # Placeholder - would calculate from actual returns
                    correlation = 0.0
                row["correlations"].append({
                    "stock": stock2,
                    "correlation": correlation
                })
            matrix.append(row)

        return {
            "stocks": stocks,
            "matrix": matrix,
            "note": "Correlation matrix requires individual stock price history"
        }

    def get_portfolio_attribution(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze portfolio performance attribution by stock and sector

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with performance attribution data
        """
        holdings_query = self.db.query(Holding)
        if account_id:
            holdings_query = holdings_query.filter(Holding.account_id == account_id)
        holdings = holdings_query.all()

        total_value = sum(h.current_value for h in holdings)
        total_pnl = sum(h.pnl for h in holdings)

        # Stock-level attribution
        stock_attribution = []
        for h in holdings:
            contribution = (h.pnl / total_pnl * 100) if total_pnl != 0 else 0
            weight = (h.current_value / total_value * 100) if total_value > 0 else 0

            stock_attribution.append({
                "stock": h.stock,
                "weight": round(weight, 2),
                "pnl": round(h.pnl, 2),
                "pnl_percent": round(h.pnl_percent, 2),
                "contribution_to_total": round(contribution, 2),
                "current_value": round(h.current_value, 2)
            })

        # Sort by contribution
        stock_attribution.sort(key=lambda x: abs(x["contribution_to_total"]), reverse=True)

        # Sector-level attribution
        sector_mapping = {
            "RELIANCE": "Energy", "TCS": "IT", "INFY": "IT", "HDFCBANK": "Banking",
            "ICICIBANK": "Banking", "SBIN": "Banking", "HINDUNILVR": "FMCG",
            "ITC": "FMCG", "TATAMOTORS": "Auto", "MARUTI": "Auto",
            "BAJFINANCE": "Finance", "AXISBANK": "Banking", "KOTAKBANK": "Banking",
            "LT": "Infrastructure", "WIPRO": "IT", "TECHM": "IT",
        }

        sector_attribution = {}
        for h in holdings:
            sector = sector_mapping.get(h.stock, "Others")
            if sector not in sector_attribution:
                sector_attribution[sector] = {
                    "value": 0,
                    "pnl": 0,
                    "count": 0
                }
            sector_attribution[sector]["value"] += h.current_value
            sector_attribution[sector]["pnl"] += h.pnl
            sector_attribution[sector]["count"] += 1

        sector_list = []
        for sector, data in sector_attribution.items():
            weight = (data["value"] / total_value * 100) if total_value > 0 else 0
            contribution = (data["pnl"] / total_pnl * 100) if total_pnl != 0 else 0

            sector_list.append({
                "sector": sector,
                "weight": round(weight, 2),
                "pnl": round(data["pnl"], 2),
                "contribution_to_total": round(contribution, 2),
                "stock_count": data["count"]
            })

        sector_list.sort(key=lambda x: abs(x["contribution_to_total"]), reverse=True)

        return {
            "total_value": total_value,
            "total_pnl": total_pnl,
            "stock_attribution": stock_attribution,
            "sector_attribution": sector_list,
            "top_contributors": stock_attribution[:5],
            "bottom_contributors": stock_attribution[-5:] if len(stock_attribution) > 5 else []
        }

    def get_drawdown_analysis(self, account_id: Optional[int] = None,
                             lookback_days: int = 365) -> Dict[str, Any]:
        """
        Enhanced drawdown analysis with rolling periods, duration tracking, and Ulcer Index

        Args:
            account_id: Filter by account ID (optional)
            lookback_days: Number of days to analyze (default: 365)

        Returns:
            Dict with comprehensive drawdown analysis
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        snapshots_query = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.recorded_at >= cutoff_date
        )
        if account_id:
            snapshots_query = snapshots_query.filter(PortfolioSnapshot.account_id == account_id)
        snapshots = snapshots_query.order_by(PortfolioSnapshot.recorded_at.asc()).all()

        if not snapshots:
            return {
                "message": "No snapshot data available for drawdown analysis",
                "lookback_days": lookback_days
            }

        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(snapshots)):
            if snapshots[i - 1].total_value > 0:
                daily_return = (snapshots[i].total_value - snapshots[i - 1].total_value) / snapshots[i - 1].total_value
                daily_returns.append(daily_return)

        # Calculate drawdown series
        drawdown_series = []
        peak_value = 0
        peak_date = None
        current_drawdown_start = None
        current_drawdown_duration = 0
        max_drawdown_duration = 0
        max_drawdown_duration_date = None

        for i, snapshot in enumerate(snapshots):
            if snapshot.total_value > peak_value:
                peak_value = snapshot.total_value
                peak_date = snapshot.recorded_at
                current_drawdown_start = None
                current_drawdown_duration = 0
            else:
                drawdown = (peak_value - snapshot.total_value) / peak_value if peak_value > 0 else 0
                drawdown_series.append({
                    "date": snapshot.recorded_at.isoformat(),
                    "value": snapshot.total_value,
                    "peak": peak_value,
                    "drawdown": drawdown,
                    "drawdown_pct": drawdown * 100
                })

                # Track drawdown duration
                if drawdown > 0:
                    if current_drawdown_start is None:
                        current_drawdown_start = snapshot.recorded_at
                    current_drawdown_duration = (snapshot.recorded_at - current_drawdown_start).days

                    if current_drawdown_duration > max_drawdown_duration:
                        max_drawdown_duration = current_drawdown_duration
                        max_drawdown_duration_date = snapshot.recorded_at.isoformat()

        # Maximum Drawdown
        max_drawdown = max([d["drawdown"] for d in drawdown_series]) if drawdown_series else 0
        max_drawdown_date = next((d["date"] for d in drawdown_series if d["drawdown"] == max_drawdown), None)

        # Average Drawdown
        avg_drawdown = sum(d["drawdown"] for d in drawdown_series) / len(drawdown_series) if drawdown_series else 0

        # Ulcer Index
        ulcer_index = 0
        if drawdown_series:
            squared_drawdowns = sum(d["drawdown"] ** 2 for d in drawdown_series)
            ulcer_index = (squared_drawdowns / len(drawdown_series)) ** 0.5

        # Rolling drawdown periods
        rolling_drawdowns = {}
        periods = [7, 30, 90]  # 7-day, 30-day, 90-day rolling

        for period in periods:
            if len(drawdown_series) >= period:
                recent_drawdowns = [d["drawdown"] for d in drawdown_series[-period:]]
                rolling_drawdowns[f"{period}_day"] = {
                    "max": max(recent_drawdowns),
                    "avg": sum(recent_drawdowns) / len(recent_drawdowns),
                    "current": recent_drawdowns[-1] if recent_drawdowns else 0
                }

        # Drawdown contribution by position (if we have position-level data)
        # This would require position-level snapshots, which we don't have
        # For now, we'll provide a placeholder
        position_contribution = []

        # Recovery time analysis
        recovery_times = []
        in_drawdown = False
        drawdown_start = None
        max_dd_in_period = 0

        for i, snapshot in enumerate(snapshots):
            if i == 0:
                peak_value = snapshot.total_value
                continue

            if snapshot.total_value >= peak_value:
                if in_drawdown and drawdown_start:
                    recovery_time = (snapshot.recorded_at - drawdown_start).days
                    recovery_times.append({
                        "start_date": drawdown_start.isoformat(),
                        "end_date": snapshot.recorded_at.isoformat(),
                        "duration_days": recovery_time,
                        "max_drawdown": max_dd_in_period * 100
                    })
                peak_value = snapshot.total_value
                in_drawdown = False
                drawdown_start = None
                max_dd_in_period = 0
            else:
                drawdown = (peak_value - snapshot.total_value) / peak_value
                if drawdown > 0:
                    if not in_drawdown:
                        in_drawdown = True
                        drawdown_start = snapshots[i - 1].recorded_at
                    max_dd_in_period = max(max_dd_in_period, drawdown)

        avg_recovery_time = sum(r["duration_days"] for r in recovery_times) / len(recovery_times) if recovery_times else 0

        return {
            "lookback_days": lookback_days,
            "data_points": len(drawdown_series),
            "max_drawdown": {
                "value": round(max_drawdown * 100, 2),
                "date": max_drawdown_date
            },
            "avg_drawdown": round(avg_drawdown * 100, 2),
            "current_drawdown": round(drawdown_series[-1]["drawdown_pct"], 2) if drawdown_series else 0,
            "ulcer_index": round(ulcer_index * 100, 2),
            "max_drawdown_duration_days": max_drawdown_duration,
            "max_drawdown_duration_date": max_drawdown_duration_date,
            "avg_recovery_time_days": round(avg_recovery_time, 1),
            "recovery_periods": len(recovery_times),
            "rolling_drawdowns": {
                k: {
                    "max_pct": round(v["max"] * 100, 2),
                    "avg_pct": round(v["avg"] * 100, 2),
                    "current_pct": round(v["current"] * 100, 2)
                }
                for k, v in rolling_drawdowns.items()
            },
            "drawdown_series": drawdown_series[-30:] if drawdown_series else [],  # Last 30 points
            "recovery_times": recovery_times[-5:] if recovery_times else []  # Last 5 recoveries
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
