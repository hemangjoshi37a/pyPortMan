"""
Advanced Portfolio Management with Strategy Combination and Multi-Strategy Portfolio
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.stats import pearsonr
import pandas as pd

from sqlalchemy.orm import Session
from kiteconnect import KiteConnect

from models import Account, Holding, Position, Order, PortfolioSnapshot
from position_sizing import PositionSizingManager
from advanced_risk_manager import AdvancedRiskManager, RiskMetrics
from backtesting import Backtester, BacktestConfig, BacktestResult
from analytics import AnalyticsManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portfolio_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class StrategyAllocation:
    """Strategy allocation details"""
    strategy_id: str
    strategy_name: str
    weight: float
    target_positions: int
    actual_positions: int
    current_capital: float
    allocated_capital: float
    pnl_today: float
    pnl_total: float
    sharpe_ratio: float
    max_drawdown: float
    correlation_to_market: float
    correlation_to_portfolio: float
    risk_level: str


@dataclass
class CombinedStrategy:
    """Represents a combined trading strategy"""
    combination_id: str
    strategies: List[str]
    weights: List[float]
    correlation_matrix: Dict = field(default_factory=dict)
    expected_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    diversification_ratio: float = 1.0
    effective_strategies: float = 0.0


class MultiStrategyPortfolio:
    """
    Multi-strategy portfolio manager with dynamic allocation
    """

    def __init__(self, db: Session):
        self.db = db
        self.position_sizing = PositionSizingManager(db)
        self.risk_manager = AdvancedRiskManager(db)
        self.analytics = AnalyticsManager(db)
        self.active_strategies = {}
        self.performance_history = {}

    def add_strategy(self,
                    strategy_name: str,
                    strategy_function: callable,
                    allocation_pct: float = 10.0,
                    risk_level: str = "moderate"):
        """
        Add a new strategy to the portfolio

        Args:
            strategy_name: Unique name for the strategy
            strategy_function: Strategy implementation
            allocation_pct: Percentage of capital to allocate
            risk_level: Risk level (low, moderate, high)
        """
        self.active_strategies[strategy_name] = {
            "function": strategy_function,
            "allocation": allocation_pct,
            "risk_level": risk_level,
            "current_positions": [],
            "performance": {
                "pnl": 0.0,
                "win_rate": 0.0,
                "sharpe": 0.0,
                "drawdown": 0.0
            }
        }

        logger.info(f"Added strategy '{strategy_name}' with {allocation_pct}% allocation")

    def remove_strategy(self, strategy_name: str):
        """Remove a strategy from the portfolio"""
        if strategy_name in self.active_strategies:
            del self.active_strategies[strategy_name]
            logger.info(f"Removed strategy '{strategy_name}'")

    def get_strategy_allocation(self, account_id: int) -> List[StrategyAllocation]:
        """
        Get current allocation for all strategies
        """
        total_capital = self.position_sizing.get_account_capital(account_id)["total_capital"]
        allocation = []

        for strategy_name, strategy_data in self.active_strategies.items():
            weight = strategy_data["allocation"]
            target_capital = total_capital * (weight / 100)

            # Get strategy performance
            performance = strategy_data.get("performance", {})

            # Placeholder for correlation calculations
            correlation_to_portfolio = 0.8  # Would calculate actual correlation

            allocation.append(
                StrategyAllocation(
                    strategy_id=strategy_name,
                    strategy_name=strategy_name,
                    weight=weight,
                    target_positions=(weight / 100) * 10,  # Assuming max 10 positions
                    actual_positions=len(strategy_data.get("current_positions", [])),
                    current_capital=total_capital,
                    allocated_capital=target_capital,
                    pnl_today=performance.get("daily_pnl", 0),
                    pnl_total=performance.get("pnl", 0),
                    sharpe_ratio=performance.get("sharpe", 0),
                    max_drawdown=performance.get("drawdown", 0),
                    correlation_to_market=1.0,  # Placeholder
                    correlation_to_portfolio=correlation_to_portfolio,
                    risk_level=strategy_data["risk_level"]
                )
            )

        return allocation

    def optimize_strategy_weights(
        self,
        account_id: int,
        target_return: Optional[float] = None,
        max_risk: float = 0.20,
        min_weight: float = 5.0,
        max_weight: float = 30.0
    ):
        """
        Optimize strategy weights using mean-variance optimization

        Args:
            account_id: Account ID
            target_return: Target return (optional)
            max_risk: Maximum portfolio risk
            min_weight: Minimum weight per strategy
            max_weight: Maximum weight per strategy
        """
        # Get strategy returns and correlations
        returns, std_devs, correlations = self._calculate_strategy_metrics(account_id)

        if not returns:
            return {"error": "Insufficient strategy performance data"}

        # Cross-validation approach
        best_weights = None
        best_sharpe = -float('inf')
        best_portfolio_metrics = None

        # Define weight ranges
        weight_ranges = np.arange(min_weight, max_weight + 1, 5)  # 5% increments

        # Generate combinations
        weight_combinations = self._generate_weight_combinations(
            list(self.active_strategies.keys()),
            weight_ranges
        )

        for weights in weight_combinations:
            # Skip if weights don't sum to 100%
            if abs(sum(weights.values()) - 100.0) > 1.0:
                continue

            # Calculate portfolio metrics
            port_return = sum(returns[s] * weights[s] for s in weights.keys())

            # Portfolio variance
            portfolio_variance = 0
            for s1 in weights.keys():
                for s2 in weights.keys():
                    weight1, weight2 = weights[s1] / 100, weights[s2] / 100
                    std1, std2 = std_devs[s1], std_devs[s2]
                    corr = correlations.get((s1, s2), 0.8)
                    portfolio_variance += weight1 * weight2 * std1 * std2 * corr

            port_volatility = np.sqrt(portfolio_variance)

            # Check constraints
            if port_volatility > max_risk:
                continue
            if target_return and port_return < target_return:
                continue

            # Calculate Sharpe ratio
            sharpe = (port_return - 0.06) / port_volatility if port_volatility > 0 else 0

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = weights
                best_portfolio_metrics = {
                    "expected_return": port_return,
                    "volatility": port_volatility,
                    "sharpe_ratio": sharpe,
                    "diversification_ratio": 1 / sum(weights[s]**2 for s in weights.keys())
                }

        return {
            "optimal_weights": best_weights,
            "portfolio_metrics": best_portfolio_metrics,
            "target_return": target_return,
            "max_risk": max_risk
        }

    def _calculate_strategy_metrics(self, account_id: int) -> Tuple[Dict, Dict, Dict]:
        """Calculate strategy performance metrics"""
        returns = {}
        std_devs = {}
        correlations = {}

        for strategy_name in self.active_strategies.keys():
            # Get strategy performance history
            performance = self._get_strategy_performance(strategy_name, account_id)

            if performance and len(performance) > 30:
                returns[strategy_name] = np.mean(performance)
                std_devs[strategy_name] = np.std(performance)

        # Calculate correlations
        for s1 in self.active_strategies.keys():
            for s2 in self.active_strategies.keys():
                if s1 != s2:
                    perf1 = self._get_strategy_performance(s1, account_id)
                    perf2 = self._get_strategy_performance(s2, account_id)

                    if len(perf1) == len(perf2) and len(perf1) > 10:
                        corr, _ = pearsonr(perf1, perf2)
                        correlations[(s1, s2)] = corr
                        correlations[(s2, s1)] = corr

        return returns, std_devs, correlations

    def _get_strategy_performance(self, strategy_name: str, account_id: int) -> List[float]:
        """Get strategy performance data"""
        # This would fetch performance data from the strategy
        # For now, return mock data
        return [0.02, -0.01, 0.03, 0.01, 0.015]  # 5-day returns

    def _generate_weight_combinations(
        self,
        strategies: List[str],
        weight_ranges: List[float]
    ) -> List[Dict[str, float]]:
        """Generate all possible weight combinations"""
        # This is a simplified version - in production use random sampling for efficiency
        combinations = []

        # Limit to 2-4 strategies to avoid combinatorial explosion
        for r in range(2, min(4, len(strategies)) + 1):
            from itertools import combinations

            strategy_combos = combinations(strategies, r)

            for combo in strategy_combos:
                # Example weight combinations
                weights = [10.0, 15.0, 25.0]  # Simplified
                weight_dict = dict(zip(combo, weights[:len(combo)]))

                # Normalize to 100%
                total = sum(weight_dict.values())
                for k in weight_dict:
                    weight_dict[k] = (weight_dict[k] / total) * 100

                combinations.append(weight_dict)

        return combinations

    def create_combined_strategy(
        self,
        strategy_names: List[str],
        weights: Optional[List[float]] = None
    ) -> CombinedStrategy:
        """
        Create a combined strategy using multiple individual strategies

        Args:
            strategy_names: Names of strategies to combine
            weights: Optional weights for each strategy

        Returns:
            CombinedStrategy object
        """
        if weights is None:
            weights = [1.0 / len(strategy_names)] * len(strategy_names)

        if len(strategy_names) != len(weights):
            raise ValueError("Number of strategies must match number of weights")

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate correlations
        correlations = {}
        returns = []
        for i, s1 in enumerate(strategy_names):
            for j, s2 in enumerate(strategy_names):
                if i != j:
                    # Would calculate actual correlation
                    correlations[(s1, s2)] = 0.5

            # Mock returns
            returns.append(0.15)  # 15% annual return

        # Calculate portfolio metrics
        expected_return = sum(r * w for r, w in zip(returns, normalized_weights))
        volatility = 0.1  # Would calculate actual portfolio volatility
        sharpe = (expected_return - 0.06) / volatility if volatility > 0 else 0

        # Diversification ratio (lower correlation = higher ratio)
        avg_correlation = np.mean(list(correlations.values())) if correlations else 0.5
        diversification_ratio = 1 / (avg_correlation + 0.1)

        # Effective number of strategies
        herfindahl = sum(w**2 for w in normalized_weights)
        effective_num = 1.0 / herfindahl

        return CombinedStrategy(
            combination_id=f"COMB_{'_'.join(strategy_names)}",
            strategies=strategy_names,
            weights=normalized_weights,
            correlation_matrix=correlations,
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            diversification_ratio=diversification_ratio,
            effective_strategies=effective_num
        )

    def rebalance_on_condition(
        self,
        account_id: int,
        trigger_types: Dict[str, float] = None
    ):
        """
        Rebalance portfolio based on conditions

        Args:
            account_id: Account ID
            trigger_types: Dictionary of trigger types and thresholds
                Example: {"drift_pct": 5, "time_days": 30, "perform_threshold": -10}
        """
        if trigger_types is None:
            trigger_types = {"drift_pct": 5.0}

        # Get current allocation
        current_allocation = self.get_strategy_allocation(account_id)

        # Check drift
        drift_trigger = trigger_types.get("drift_pct", 5.0)
        if self._check_allocation_drift(current_allocation, drift_trigger):
            logger.info(f"Rebalancing triggered: Allocation drift exceeds {drift_trigger}%")
            return self._execute_rebalancing(account_id, current_allocation)

        # Check time-based rebalancing
        time_trigger = trigger_types.get("time_days", 30)
        if self._check_rebalance_time(account_id, time_trigger):
            logger.info(f"Rebalancing triggered: Time since last rebalance exceeds {time_trigger} days")
            return self._execute_rebalancing(account_id, current_allocation)

        return {"status": "no_rebalance", "reason": "No triggers met"}

    def _check_allocation_drift(self, allocation: List[StrategyAllocation], drift_pct: float) -> bool:
        """Check if allocation has drifted beyond threshold"""
        for strat in allocation:
            target = strat.weight
            actual = strat.actual_positions / max(strat.target_positions, 1) * 100
            drift = abs(actual - target)

            if drift > drift_pct:
                return True

        return False

    def _check_rebalance_time(self, account_id: int, days: int) -> bool:
        """Check if it's time to rebalance based on schedule"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Check orders history
        orders = self.db.query(Order).filter(
            Order.account_id == account_id,
            Order.placed_at >= cutoff_date
        ).all()

        return len(orders) == 0  # No recent activity

    def _execute_rebalancing(self, account_id: int, allocation: List[StrategyAllocation]):
        """Execute rebalancing based on optimized weights"""
        # Get optimized weights
        optimization = self.optimize_strategy_weights(account_id)

        if "error" in optimization:
            return {"status": "failed", "reason": optimization["error"]}

        optimized_weights = optimization["optimal_weights"]

        # Calculate trades needed
        trades = []
        for strat in allocation:
            target_weight = optimized_weights.get(strat.strategy_name, strat.weight / 100)
            current_weight = strat.actual_positions / max(strat.target_positions, 1)

            delta = target_weight - current_weight
            if abs(delta) > 0.01:  # Rebalance if difference > 1%
                trades.append({
                    "strategy": strat.strategy_name,
                    "action": "increase" if delta > 0 else "decrease",
                    "pct_change": abs(delta) * 100
                })

        return {
            "status": "rebalancing",
            "trades": trades,
            "target_weights": optimized_weights,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_portfolio_health_score(self, account_id: int) -> Tuple[float, Dict]:
        """
        Calculate overall portfolio health score

        Returns:
            Health score (0-100) and detailed breakdown
        """
        score = 100.0
        breakdown = {}

        # Get overall portfolio metrics
        risk_metrics = self.risk_manager.monitor_real_time_risk(account_id)

        # Deduct for high risk
        if risk_metrics.risk_level == "critical":
            breakdown["risk_level"] = -30
            score += breakdown["risk_level"]
        elif risk_metrics.risk_level == "high":
            breakdown["risk_level"] = -15
            score += breakdown["risk_level"]

        # Deduct for high drawdown
        if risk_metrics.max_drawdown > 0.20:
            breakdown["drawdown"] = -20
            score += breakdown["drawdown"]
        elif risk_metrics.max_drawdown > 0.10:
            breakdown["drawdown"] = -10
            score += breakdown["drawdown"]

        # Deduct for poor Sharpe ratio
        if risk_metrics.sharpe_ratio < 0.5:
            breakdown["sharpe"] = -10
            score += breakdown["sharpe"]

        # Deduct for low diversification
        num_strategies = len(self.active_strategies)
        if num_strategies < 3:
            breakdown["diversification"] = -10
            score += breakdown["diversification"]

        # Ensure score is within bounds
        score = max(0.0, min(100.0, score))

        return score, breakdown

    def generate_portfolio_report(self, account_id: int) -> Dict[str, Any]:
        """Generate comprehensive portfolio report"""
        allocation = self.get_strategy_allocation(account_id)
        optimization_result = self.optimize_strategy_weights(account_id)
        health_score, breakdown = self.get_portfolio_health_score(account_id)
        risk_summary = self.risk_manager.get_risk_summary(account_id)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "account_id": account_id,
            "current_allocation": allocation,
            "optimized_allocation": optimization_result.get("optimal_weights"),
            "portfolio_metrics": optimization_result.get("portfolio_metrics"),
            "health_score": round(health_score, 1),
            "health_breakdown": breakdown,
            "risk_metrics": risk_summary,
            "recommendations": self._generate_portfolio_recommendations(allocation, health_score)
        }

    def _generate_portfolio_recommendations(
        self,
        allocation: List[StrategyAllocation],
        health_score: float
    ) -> List[Dict[str, Any]]:
        """Generate portfolio improvement recommendations"""
        recommendations = []

        # Based on health score
        if health_score < 50:
            recommendations.append({
                "priority": "critical",
                "area": "risk_management",
                "message": "Portfolio health is critically low. Immediate action required."
            })
        elif health_score < 70:
            recommendations.append({
                "priority": "high",
                "area": "risk_management",
                "message": "Portfolio health is below target. Review risk parameters."
            })

        # Based on diversification
        if len(allocation) < 3:
            recommendations.append({
                "priority": "medium",
                "area": "diversification",
                "message": "Add more strategies to improve diversification."
            })

        return recommendations


if __name__ == "__main__":
    from database import SessionLocal

    db = SessionLocal()
    ms_portfolio = MultiStrategyPortfolio(db)

    # Test portfolio health
    health, breakdown = ms_portfolio.get_portfolio_health_score(1)
    print(f"Portfolio Health Score: {health}/100")

    db.close()
