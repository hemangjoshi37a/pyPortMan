"""
Advanced Risk Management System for pyPortMan
Real-time risk monitoring, dynamic position sizing, and portfolio risk controls
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from sqlalchemy.orm import Session
from kiteconnect import KiteConnect

from models import Account, Position, Holding, Order, PortfolioSnapshot
from position_sizing import PositionSizingManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Real-time risk metrics"""
    account_id: int
    timestamp: datetime
    total_capital: float
    available_margin: float
    total_position_value: float
    exposure_percentage: float
    daily_var_95: float
    daily_var_99: float
    max_single_position_pct: float
    concentration_risk: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    current_drawdown: float
    risk_level: RiskLevel
    margin_used_pct: float
    positions_at_risk: int
    positions_healthy: int
    score: float = 0.0


@dataclass
class RiskLimits:
    """Risk limits and thresholds"""
    max_position_size_pct: float = 10.0
    max_sector_exposure_pct: float = 25.0
    max_portfolio_drawdown_pct: float = 15.0
    daily_var_limit_pct: float = 5.0
    max_leverage: float = 2.0
    min_margin_buffer_pct: float = 20.0
    max_concentration_pct: float = 15.0


class AdvancedRiskManager:
    """
    Advanced Risk Management System with real-time monitoring
    """

    def __init__(self, db: Session, kite: Optional[KiteConnect] = None):
        self.db = db
        self.kite = kite
        self.position_sizing = PositionSizingManager(db)
        self.risk_limits = RiskLimits()
        self.risk_history: List[Dict] = []
        self.alerts = []

    def calculate_portfolio_var(self, account_id: int, confidence_level: float = 0.95) -> float:
        """
        Calculate Value at Risk using historical simulation method

        Args:
            account_id: Account ID
            confidence_level: Confidence level (0.95 for 95% VaR)

        Returns:
            VaR value in currency
        """
        # Get historical data for positions
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= cutoff_date
        ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

        if len(snapshots) < 2:
            return 0.0

        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(snapshots)):
            if snapshots[i-1].total_value > 0:
                daily_return = (snapshots[i].total_value - snapshots[i-1].total_value) / snapshots[i-1].total_value
                daily_returns.append(daily_return)

        if not daily_returns:
            return 0.0

        # Calculate VaR using historical simulation
        sorted_returns = sorted(daily_returns)
        var_index = int(len(sorted_returns) * (1 - confidence_level))
        var_return = sorted_returns[var_index] if var_index < len(sorted_returns) else 0

        # Current portfolio value
        current_value = snapshots[-1].total_value if snapshots else 0

        return abs(var_return * current_value)

    def calculate_portfolio_beta(self, account_id: int) -> float:
        """
        Calculate portfolio beta relative to market (NIFTY as proxy)

        Args:
            account_id: Account ID

        Returns:
            Portfolio beta
        """
        # This would typically use market data
        # For now, return a simplified calculation
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

        if not holdings:
            return 1.0

        # Calculate weighted average beta
        # In production, this would fetch actual beta values
        total_value = sum(h.current_value for h in holdings)
        weighted_beta = 0.0

        for holding in holdings:
            # Placeholder - should fetch actual beta from API or database
            stock_beta = 1.0
            weight = holding.current_value / total_value
            weighted_beta += stock_beta * weight

        return weighted_beta

    def monitor_real_time_risk(self, account_id: int) -> RiskMetrics:
        """
        Monitor real-time risk metrics

        Args:
            account_id: Account ID

        Returns:
            RiskMetrics object
        """
        # Get account capital and positions
        capital = self.position_sizing.get_account_capital(account_id)
        positions = self.db.query(Position).filter(Position.account_id == account_id).all()
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

        # Calculate exposure
        total_position_value = sum(abs(p.qty * p.ltp) for p in positions) + sum(h.current_value for h in holdings)
        exposure_pct = (total_position_value / capital["total_capital"] * 100) if capital["total_capital"] > 0 else 0

        # Calculate VaR
        daily_var_95 = self.calculate_portfolio_var(account_id, 0.95)
        daily_var_99 = self.calculate_portfolio_var(account_id, 0.99)

        # Calculate concentration risk
        max_single_position = 0
        if positions:
            max_single_position = max(abs(p.qnl * p.ltp) for p in positions)
        if holdings:
            max_single_position = max(max_single_position, max(h.current_value for h in holdings))

        max_single_position_pct = (max_single_position / capital["total_capital"] * 100) if capital["total_capital"] > 0 else 0
        concentration_risk = max_single_position_pct

        # Estimate Sharpe and Sortino ratios from available data
        sharpe_ratio = self.estimate_sharpe_ratio(account_id)
        sortino_ratio = self.estimate_sortino_ratio(account_id)

        # Calculate drawdown metrics
        max_dd, current_dd = self.calculate_drawdown_metrics(account_id)

        # Determine risk level
        risk_level = self._determine_risk_level(exposure_pct, max_single_position_pct, max_dd)

        # Count positions at risk
        positions_at_risk = sum(1 for p in positions if p.pnl_percent < -5)         positions_healthy = sum(1 for p in positions if p.pnl_percent > 0)

        # Calculate risk score
        score = self._calculate_risk_score(exposure_pct, max_single_position_pct, sharpe_ratio, max_dd, positions_at_risk, len(positions))

        risk_metrics = RiskMetrics(
            account_id=account_id,
            timestamp=datetime.utcnow(),
            total_capital=capital["total_capital"],
            available_margin=capital["available_margin"],
            total_position_value=total_position_value,
            exposure_percentage=exposure_pct,
            daily_var_95=daily_var_95,
            daily_var_99=daily_var_99,
            max_single_position_pct=max_single_position_pct,
            concentration_risk=concentration_risk,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_dd,
            current_drawdown=current_dd,
            risk_level=risk_level,
            margin_used_pct=(capital["used_margin"] / capital["total_capital"] * 100) if capital["total_capital"] > 0 else 0,
            positions_at_risk=positions_at_risk,
            positions_healthy=positions_healthy,
            score=score
        )

        # Store in history
        self.risk_history.append({
            "timestamp": datetime.utcnow(),
            "account_id": account_id,
            "metrics": risk_metrics.__dict__
        })

        # Check risk limits and generate alerts
        self._check_risk_limits(risk_metrics)

        return risk_metrics

    def estimate_sharpe_ratio(self, account_id: int) -> float:
        """Estimate Sharpe ratio from available data"""
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.desc()).limit(30).all()

        if len(snapshots) < 2:
            return 0.0

        returns = []
        for i in range(1, len(snapshots)):
            if snapshots[i-1].total_value > 0:
                daily_return = (snapshots[i].total_value - snapshots[i-1].total_value) / snapshots[i-1].total_value
                returns.append(daily_return)

        if not returns:
            return 0.0

        avg_return = np.mean(returns)
        std_dev = np.std(returns)

        # Assume risk-free rate of 6% annually
        risk_free_rate = 0.06 / 252

        if std_dev > 0:
            sharpe = (avg_return - risk_free_rate) / std_dev * np.sqrt(252)
            return sharpe

        return 0.0

    def estimate_sortino_ratio(self, account_id: int) -> float:
        """Estimate Sortino ratio from available data"""
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.desc()).limit(30).all()

        if len(snapshots) < 2:
            return 0.0

        returns = []
        for i in range(1, len(snapshots)):
            if snapshots[i-1].total_value > 0:
                daily_return = (snapshots[i].total_value - snapshots[i-1].total_value) / snapshots[i-1].total_value
                returns.append(daily_return)

        if not returns:
            return 0.0

        avg_return = np.mean(returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return self.estimate_sharpe_ratio(account_id)

        downside_dev = np.std(downside_returns)
        risk_free_rate = 0.06 / 252

        if downside_dev > 0:
            sortino = (avg_return - risk_free_rate) / downside_dev * np.sqrt(252)
            return sortino

        return 0.0

    def calculate_drawdown_metrics(self, account_id: int) -> Tuple[float, float]:
        """Calculate max and current drawdown"""
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

        if not snapshots:
            return 0.0, 0.0

        max_drawdown = 0.0
        current_drawdown = 0.0
        peak = snapshots[0].total_value

        for snapshot in snapshots:
            if snapshot.total_value > peak:
                peak = snapshot.total_value

            drawdown = (peak - snapshot.total_value) / peak if peak > 0 else 0

            if drawdown > max_drawdown:
                max_drawdown = drawdown

            if snapshot.recorded_at == snapshots[-1].recorded_at:
                current_drawdown = drawdown

        return max_drawdown, current_drawdown

    def dynamic_position_sizing(self, account_id: int, stock_price: float, volatility: float, correlation: float = 0.5) -> Dict[str, Any]:
        """
        Calculate dynamic position size based on volatility and correlation

        Args:
            account_id: Account ID
            stock_price: Current stock price
            volatility: Stock volatility
            correlation: Correlation with portfolio

        Returns:
            Position sizing recommendation
        """
        # Get base position size from fixed fractional method
        base_sizing = self.position_sizing.calculate_fixed_fractional(
            account_id, stock_price, risk_per_trade_pct=2.0
        )

        # Adjust based on volatility
        # Higher volatility = smaller position
        target_volatility = 0.02  # 2% daily volatility target
        volatility_adjustment = min(1.0, target_volatility / (volatility + 0.0001))

        # Adjust based on correlation
        # Higher correlation = smaller position (for diversification)
        correlation_penalty = 1.0 - (correlation * 0.5)

        # Combined adjustment
        combined_adjustment = volatility_adjustment * correlation_penalty

        # Adjust quantity
        adjusted_quantity = int(base_sizing["quantity"] * combined_adjustment)

        return {
            "strategy": "dynamic",
            "base_quantity": base_sizing["quantity"],
            "adjusted_quantity": adjusted_quantity,
            "volatility_adjustment": volatility_adjustment,
            "correlation_penalty": correlation_penalty,
            "position_value": adjusted_quantity * stock_price,
            "risk_per_trade_pct": base_sizing["risk_per_trade_pct"],
            "reasoning": f"Vol: {volatility:.2%}, Corr: {correlation:.2f}"
        }

    def _determine_risk_level(self, exposure_pct: float, max_single_position_pct: float, max_drawdown: float) -> RiskLevel:
        """Determine overall risk level"""
        risk_score = 0

        if exposure_pct > 80:
            risk_score += 3
        elif exposure_pct > 60:
            risk_score += 2
        elif exposure_pct > 40:
            risk_score += 1

        if max_single_position_pct > 10:
            risk_score += 2
        elif max_single_position_pct > 7:
            risk_score += 1

        if max_drawdown > 0.15:
            risk_score += 3
        elif max_drawdown > 0.10:
            risk_score += 2
        elif max_drawdown > 0.05:
            risk_score += 1

        if risk_score >= 7:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

    def _calculate_risk_score(self, exposure_pct: float, concentration: float, sharpe: float,
                            max_dd: float, positions_at_risk: int, total_positions: int) -> float:
        """Calculate risk score (0-100, lower is better)"""
        score = 100

        # Deduct for high exposure
        if exposure_pct > 80:
            score -= 30
        elif exposure_pct > 60:
            score -= 20
        elif exposure_pct > 40:
            score -= 10

        # Deduct for concentration
        if concentration > 15:
            score -= 20
        elif concentration > 10:
            score -= 10

        # Deduct for poor Sharpe ratio
        if sharpe < 0.5:
            score -= 15
        elif sharpe < 1.0:
            score -= 5

        # Deduct for drawdown
        if max_dd > 0.15:
            score -= 25
        elif max_dd > 0.10:
            score -= 15
        elif max_dd > 0.05:
            score -= 5

        # Deduct for positions at risk
        if total_positions > 0:
            risk_ratio = positions_at_risk / total_positions
            if risk_ratio > 0.5:
                score -= 10
            elif risk_ratio > 0.3:
                score -= 5

        return max(0, score)

    def _check_risk_limits(self, metrics: RiskMetrics):
        """Check if risk metrics exceed limits and generate alerts"""
        alerts = []

        if metrics.exposure_percentage > self.risk_limits.max_sector_exposure_pct:
            alerts.append({
                "type": "warning",
                "message": f"Portfolio exposure {metrics.exposure_percentage:.1f}% exceeds limit of {self.risk_limits.max_sector_exposure_pct}%"
            })

        if metrics.max_single_position_pct > self.risk_limits.max_concentration_pct:
            alerts.append({
                "type": "warning",
                "message": f"Single position concentration {metrics.max_single_position_pct:.1f}% exceeds limit of {self.risk_limits.max_concentration_pct}%"
            })

        if metrics.max_drawdown > self.risk_limits.max_portfolio_drawdown_pct / 100:
            alerts.append({
                "type": "danger",
                "message": f"Maximum drawdown {metrics.max_drawdown:.1%} exceeds limit of {self.risk_limits.max_portfolio_drawdown_pct:.1%}"
            })

        if metrics.daily_var_95 > (metrics.total_capital * self.risk_limits.daily_var_limit_pct / 100):
            alerts.append({
                "type": "warning",
                "message": f"VaR (95%) ₹{metrics.daily_var_95:,.0f} exceeds daily limit"
            })

        if metrics.risk_level == RiskLevel.CRITICAL:
            alerts.append({
                "type": "danger",
                "message": "CRITICAL RISK LEVEL - Immediate action required"
            })

        self.alerts.extend(alerts)

    def get_risk_summary(self, account_id: int) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        metrics = self.monitor_real_time_risk(account_id)

        return {
            "risk_level": metrics.risk_level.value,
            "risk_score": round(metrics.score, 1),
            "metrics": metrics.__dict__,
            "limits": self.risk_limits.__dict__,
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "recommendations": self._generate_recommendations(metrics)
        }

    def _generate_recommendations(self, metrics: RiskMetrics) -> List[Dict[str, str]]:
        """Generate risk management recommendations"""
        recommendations = []

        if metrics.exposure_percentage > 70:
            recommendations.append({
                "priority": "high",
                "action": "reduce_exposure",
                "message": f"Reduce portfolio exposure from {metrics.exposure_percentage:.1f}% to below 70%"
            })

        if metrics.max_single_position_pct > 10:
            recommendations.append({
                "priority": "medium",
                "action": "diversify",
                "message": f"Reduce concentration in single position ({metrics.max_single_position_pct:.1f}%)"
            })

        if metrics.current_drawdown > 0.10:
            recommendations.append({
                "priority": "high",
                "action": "review_strategies",
                "message": f"Current drawdown of {metrics.current_drawdown:.1%} requires strategy review"
            })

        if metrics.positions_at_risk > metrics.positions_healthy:
            recommendations.append({
                "priority": "medium",
                "action": "cut_losses",
                "message": f"More losing positions ({metrics.positions_at_risk}) than winning ones ({metrics.positions_healthy})"
            })

        if metrics.score > 70:
            recommendations.append({
                "priority": "high",
                "action": "comprehensive_review",
                "message": "High risk score indicates need for comprehensive portfolio review"
            })

        if not recommendations:
            recommendations.append({
                "priority": "low",
                "action": "monitor",
                "message": "Portfolio risk is within acceptable limits"
            })

        return recommendations

    def get_historical_risk_analysis(self, account_id: int, days: int = 30) -> Dict[str, Any]:
        """Get historical risk analysis"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        risk_entries = [entry for entry in self.risk_history
                       if entry["account_id"] == account_id and
                       entry["timestamp"] >= cutoff_date]

        if not risk_entries:
            return {"message": "No historical risk data available"}

        scores = [entry["metrics"]["score"] for entry in risk_entries]
        exposures = [entry["metrics"]["exposure_percentage"] for entry in risk_entries]
        drawdowns = [entry["metrics"]["current_drawdown"] for entry in risk_entries]

        return {
            "period_days": days,
            "data_points": len(risk_entries),
            "avg_risk_score": np.mean(scores) if scores else 0,
            "max_risk_score": max(scores) if scores else 0,
            "min_risk_score": min(scores) if scores else 0,
            "avg_exposure": np.mean(exposures) if exposures else 0,
            "max_exposure": max(exposures) if exposures else 0,
            "avg_drawdown": np.mean(drawdowns) if drawdowns else 0,
            "max_drawdown": max(drawdowns) if drawdowns else 0,
            "risk_trend": self._calculate_trend(scores),
            "alerts_generated": len(self.alerts)
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 5:
            return "insufficient_data"

        recent = values[-5:]
        half = len(recent) // 2
        first_half = recent[:half]
        second_half = recent[half:]

        if sum(first_half) < sum(second_half):
            return "improving"
        elif sum(first_half) > sum(second_half):
            return "deteriorating"
        else:
            return "stable"


if __name__ == "__main__":
    from database import SessionLocal

    db = SessionLocal()
    risk_manager = AdvancedRiskManager(db)

    # Test risk monitoring
    risk_summary = risk_manager.get_risk_summary(1)
    print(f"Risk Level: {risk_summary['risk_level']}")
    print(f"Risk Score: {risk_summary['risk_score']}")

    db.close()
