"""
Monte Carlo Simulation Module for pyPortMan
Portfolio risk analysis using Monte Carlo simulation methods
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum

from models import Account, Holding, Position, PortfolioSnapshot

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


class SimulationMethod(Enum):
    """Monte Carlo simulation methods"""
    GEOMETRIC_BROWNIAN_MOTION = "geometric_brownian_motion"
    HISTORICAL_BOOTSTRAP = "historical_bootstrap"
    PARAMETRIC_BOOTSTRAP = "parametric_bootstrap"
    ANTITHETIC_VARIATES = "antithetic_variates"
    CONTROL_VARIATES = "control_variates"


@dataclass
class SimulationResult:
    """Result of a Monte Carlo simulation"""
    method: str
    num_simulations: int
    time_horizon_days: int
    initial_value: float
    final_values: List[float]
    paths: List[List[float]]
    statistics: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    risk_metrics: Dict[str, float]


class MonteCarloSimulator:
    """
    Monte Carlo simulation for portfolio risk analysis
    Simulates future portfolio values under various scenarios
    """

    def __init__(self, db: Session):
        self.db = db

    def get_historical_returns(
        self,
        account_id: int,
        days: int = 252
    ) -> np.ndarray:
        """
        Get historical daily returns for an account

        Args:
            account_id: Account ID
            days: Number of days of historical data

        Returns:
            Array of daily returns
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= cutoff_date
        ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

        if len(snapshots) < 2:
            raise ValueError(f"Insufficient historical data. Found {len(snapshots)} snapshots.")

        # Calculate daily returns
        returns = []
        for i in range(1, len(snapshots)):
            if snapshots[i - 1].total_value > 0:
                daily_return = (snapshots[i].total_value - snapshots[i - 1].total_value) / snapshots[i - 1].total_value
                returns.append(daily_return)

        return np.array(returns)

    def simulate_geometric_brownian_motion(
        self,
        account_id: int,
        num_simulations: int = 1000,
        time_horizon_days: int = 30,
        method: SimulationMethod = SimulationMethod.GEOMETRIC_BROWNIAN_MOTION
    ) -> SimulationResult:
        """
        Simulate portfolio using Geometric Brownian Motion (GBM)

        Args:
            account_id: Account ID
            num_simulations: Number of simulation paths
            time_horizon_days: Time horizon in days
            method: Simulation method to use

        Returns:
            SimulationResult with all simulation data
        """
        # Get historical returns
        returns = self.get_historical_returns(account_id)

        # Calculate parameters
        mu = np.mean(returns)  # Daily drift
        sigma = np.std(returns)  # Daily volatility

        # Get current portfolio value
        current_snapshot = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.desc()).first()

        if not current_snapshot:
            raise ValueError("No portfolio snapshot found")

        S0 = current_snapshot.total_value
        dt = 1  # Daily time step

        # Generate simulation paths
        paths = []
        final_values = []

        for _ in range(num_simulations):
            path = [S0]
            current_value = S0

            for _ in range(time_horizon_days):
                if method == SimulationMethod.ANTITHETIC_VARIATES:
                    # Use antithetic variates for variance reduction
                    z1 = np.random.standard_normal()
                    z2 = -z1
                    z = (z1 + z2) / 2
                else:
                    z = np.random.standard_normal()

                # GBM formula: S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*z*sqrt(dt))
                next_value = current_value * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * z * np.sqrt(dt))
                path.append(next_value)
                current_value = next_value

            paths.append(path)
            final_values.append(current_value)

        # Calculate statistics
        final_values = np.array(final_values)
        statistics = self._calculate_statistics(final_values, S0)

        # Calculate confidence intervals
        confidence_intervals = {
            "90%": np.percentile(final_values, [5, 95]),
            "95%": np.percentile(final_values, [2.5, 97.5]),
            "99%": np.percentile(final_values, [0.5, 99.5])
        }

        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(final_values, S0, time_horizon_days)

        return SimulationResult(
            method=method.value,
            num_simulations=num_simulations,
            time_horizon_days=time_horizon_days,
            initial_value=S0,
            final_values=final_values.tolist(),
            paths=paths,
            statistics=statistics,
            confidence_intervals=confidence_intervals,
            risk_metrics=risk_metrics
        )

    def simulate_historical_bootstrap(
        self,
        account_id: int,
        num_simulations: int = 1000,
        time_horizon_days: int = 30
    ) -> SimulationResult:
        """
        Simulate using historical bootstrap method
        Resamples historical returns to create future paths

        Args:
            account_id: Account ID
            num_simulations: Number of simulation paths
            time_horizon_days: Time horizon in days

        Returns:
            SimulationResult with all simulation data
        """
        # Get historical returns
        returns = self.get_historical_returns(account_id)

        # Get current portfolio value
        current_snapshot = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.desc()).first()

        if not current_snapshot:
            raise ValueError("No portfolio snapshot found")

        S0 = current_snapshot.total_value

        # Generate simulation paths using bootstrap
        paths = []
        final_values = []

        for _ in range(num_simulations):
            path = [S0]
            current_value = S0

            for _ in range(time_horizon_days):
                # Randomly sample from historical returns
                sampled_return = np.random.choice(returns)
                next_value = current_value * (1 + sampled_return)
                path.append(next_value)
                current_value = next_value

            paths.append(path)
            final_values.append(current_value)

        # Calculate statistics
        final_values = np.array(final_values)
        statistics = self._calculate_statistics(final_values, S0)

        # Calculate confidence intervals
        confidence_intervals = {
            "90%": np.percentile(final_values, [5, 95]),
            "95%": np.percentile(final_values, [2.5, 97.5]),
            "99%": np.percentile(final_values, [0.5, 99.5])
        }

        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(final_values, S0, time_horizon_days)

        return SimulationResult(
            method="historical_bootstrap",
            num_simulations=num_simulations,
            time_horizon_days=time_horizon_days,
            initial_value=S0,
            final_values=final_values.tolist(),
            paths=paths,
            statistics=statistics,
            confidence_intervals=confidence_intervals,
            risk_metrics=risk_metrics
        )

    def simulate_parametric_bootstrap(
        self,
        account_id: int,
        num_simulations: int = 1000,
        time_horizon_days: int = 30
    ) -> SimulationResult:
        """
        Simulate using parametric bootstrap method
        Fits a distribution to historical returns and samples from it

        Args:
            account_id: Account ID
            num_simulations: Number of simulation paths
            time_horizon_days: Time horizon in days

        Returns:
            SimulationResult with all simulation data
        """
        # Get historical returns
        returns = self.get_historical_returns(account_id)

        # Fit normal distribution to returns
        mu = np.mean(returns)
        sigma = np.std(returns)

        # Get current portfolio value
        current_snapshot = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.desc()).first()

        if not current_snapshot:
            raise ValueError("No portfolio snapshot found")

        S0 = current_snapshot.total_value

        # Generate simulation paths
        paths = []
        final_values = []

        for _ in range(num_simulations):
            path = [S0]
            current_value = S0

            for _ in range(time_horizon_days):
                # Sample from fitted normal distribution
                sampled_return = np.random.normal(mu, sigma)
                next_value = current_value * (1 + sampled_return)
                path.append(next_value)
                current_value = next_value

            paths.append(path)
            final_values.append(current_value)

        # Calculate statistics
        final_values = np.array(final_values)
        statistics = self._calculate_statistics(final_values, S0)

        # Calculate confidence intervals
        confidence_intervals = {
            "90%": np.percentile(final_values, [5, 95]),
            "95%": np.percentile(final_values, [2.5, 97.5]),
            "99%": np.percentile(final_values, [0.5, 99.5])
        }

        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(final_values, S0, time_horizon_days)

        return SimulationResult(
            method="parametric_bootstrap",
            num_simulations=num_simulations,
            time_horizon_days=time_horizon_days,
            initial_value=S0,
            final_values=final_values.tolist(),
            paths=paths,
            statistics=statistics,
            confidence_intervals=confidence_intervals,
            risk_metrics=risk_metrics
        )

    def simulate_stress_scenarios(
        self,
        account_id: int,
        scenarios: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Simulate portfolio under various stress scenarios

        Args:
            account_id: Account ID
            scenarios: List of stress scenarios (default scenarios if None)

        Returns:
            Dict with scenario results
        """
        # Get current portfolio value
        current_snapshot = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.desc()).first()

        if not current_snapshot:
            raise ValueError("No portfolio snapshot found")

        S0 = current_snapshot.total_value

        # Default stress scenarios
        if scenarios is None:
            scenarios = [
                {"name": "Market Crash (-20%)", "daily_return": -0.20, "days": 1},
                {"name": "Severe Crash (-30%)", "daily_return": -0.30, "days": 1},
                {"name": "Flash Crash (-10%)", "daily_return": -0.10, "days": 1},
                {"name": "Bear Market (-5% daily for 10 days)", "daily_return": -0.05, "days": 10},
                {"name": "Prolonged Bear (-3% daily for 20 days)", "daily_return": -0.03, "days": 20},
                {"name": "Moderate Decline (-2% daily for 30 days)", "daily_return": -0.02, "days": 30},
                {"name": "Bull Run (+10% daily for 5 days)", "daily_return": 0.10, "days": 5},
                {"name": "Moderate Growth (+2% daily for 30 days)", "daily_return": 0.02, "days": 30},
            ]

        results = []

        for scenario in scenarios:
            final_value = S0 * ((1 + scenario["daily_return"]) ** scenario["days"])
            loss = S0 - final_value
            loss_pct = (loss / S0 * 100) if S0 > 0 else 0

            results.append({
                "scenario_name": scenario["name"],
                "daily_return": scenario["daily_return"],
                "days": scenario["days"],
                "initial_value": S0,
                "final_value": final_value,
                "loss": loss,
                "loss_pct": loss_pct,
                "survives": final_value > 0
            })

        return {
            "account_id": account_id,
            "initial_value": S0,
            "scenarios": results,
            "worst_case": min(results, key=lambda x: x["final_value"]),
            "best_case": max(results, key=lambda x: x["final_value"])
        }

    def _calculate_statistics(self, final_values: np.ndarray, initial_value: float) -> Dict[str, float]:
        """Calculate statistics from simulation results"""
        return {
            "mean": float(np.mean(final_values)),
            "median": float(np.median(final_values)),
            "std": float(np.std(final_values)),
            "min": float(np.min(final_values)),
            "max": float(np.max(final_values)),
            "expected_return": float((np.mean(final_values) - initial_value) / initial_value * 100),
            "expected_return_pct": float((np.mean(final_values) - initial_value) / initial_value * 100),
            "probability_of_profit": float(np.sum(final_values > initial_value) / len(final_values) * 100),
            "probability_of_loss": float(np.sum(final_values < initial_value) / len(final_values) * 100)
        }

    def _calculate_risk_metrics(
        self,
        final_values: np.ndarray,
        initial_value: float,
        time_horizon_days: int
    ) -> Dict[str, float]:
        """Calculate risk metrics from simulation results"""
        # Value at Risk (VaR)
        var_90 = initial_value - np.percentile(final_values, 10)
        var_95 = initial_value - np.percentile(final_values, 5)
        var_99 = initial_value - np.percentile(final_values, 1)

        # Conditional VaR (Expected Shortfall)
        var_95_threshold = np.percentile(final_values, 5)
        cvar_95 = initial_value - np.mean(final_values[final_values <= var_95_threshold])

        # Maximum Drawdown in simulation
        max_drawdown = 0
        for path in final_values:
            drawdown = (initial_value - path) / initial_value if initial_value > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        return {
            "var_90": float(var_90),
            "var_95": float(var_95),
            "var_99": float(var_99),
            "var_90_pct": float(var_90 / initial_value * 100) if initial_value > 0 else 0,
            "var_95_pct": float(var_95 / initial_value * 100) if initial_value > 0 else 0,
            "var_99_pct": float(var_99 / initial_value * 100) if initial_value > 0 else 0,
            "cvar_95": float(cvar_95),
            "cvar_95_pct": float(cvar_95 / initial_value * 100) if initial_value > 0 else 0,
            "max_drawdown": float(max_drawdown),
            "max_drawdown_pct": float(max_drawdown * 100),
            "time_horizon_days": time_horizon_days
        }

    def compare_simulation_methods(
        self,
        account_id: int,
        num_simulations: int = 1000,
        time_horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Compare different simulation methods

        Args:
            account_id: Account ID
            num_simulations: Number of simulations per method
            time_horizon_days: Time horizon in days

        Returns:
            Dict with comparison of all methods
        """
        methods = [
            SimulationMethod.GEOMETRIC_BROWNIAN_MOTION,
            SimulationMethod.HISTORICAL_BOOTSTRAP,
            SimulationMethod.PARAMETRIC_BOOTSTRAP,
            SimulationMethod.ANTITHETIC_VARIATES
        ]

        results = {}

        for method in methods:
            try:
                if method == SimulationMethod.HISTORICAL_BOOTSTRAP:
                    result = self.simulate_historical_bootstrap(account_id, num_simulations, time_horizon_days)
                elif method == SimulationMethod.PARAMETRIC_BOOTSTRAP:
                    result = self.simulate_parametric_bootstrap(account_id, num_simulations, time_horizon_days)
                else:
                    result = self.simulate_geometric_brownian_motion(account_id, num_simulations, time_horizon_days, method)

                results[method.value] = {
                    "mean": result.statistics["mean"],
                    "median": result.statistics["median"],
                    "std": result.statistics["std"],
                    "var_95": result.risk_metrics["var_95"],
                    "probability_of_profit": result.statistics["probability_of_profit"]
                }
            except Exception as e:
                logger.error(f"Error in {method.value} simulation: {e}")
                results[method.value] = {"error": str(e)}

        return {
            "account_id": account_id,
            "num_simulations": num_simulations,
            "time_horizon_days": time_horizon_days,
            "methods": results
        }

    def get_simulation_summary(
        self,
        account_id: int,
        num_simulations: int = 1000,
        time_horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive simulation summary

        Args:
            account_id: Account ID
            num_simulations: Number of simulations
            time_horizon_days: Time horizon in days

        Returns:
            Dict with comprehensive simulation summary
        """
        # Run GBM simulation
        gbm_result = self.simulate_geometric_brownian_motion(
            account_id, num_simulations, time_horizon_days
        )

        # Run stress scenarios
        stress_result = self.simulate_stress_scenarios(account_id)

        # Get historical data for context
        returns = self.get_historical_returns(account_id)
        historical_volatility = np.std(returns) * np.sqrt(252)  # Annualized

        return {
            "account_id": account_id,
            "simulation": {
                "method": gbm_result.method,
                "num_simulations": num_simulations,
                "time_horizon_days": time_horizon_days,
                "initial_value": gbm_result.initial_value,
                "expected_final_value": gbm_result.statistics["mean"],
                "expected_return_pct": gbm_result.statistics["expected_return_pct"],
                "probability_of_profit": gbm_result.statistics["probability_of_profit"],
                "confidence_intervals": gbm_result.confidence_intervals,
                "risk_metrics": gbm_result.risk_metrics
            },
            "stress_scenarios": stress_result,
            "historical_context": {
                "historical_volatility_annual": float(historical_volatility),
                "historical_volatility_daily": float(np.std(returns)),
                "historical_mean_return_daily": float(np.mean(returns)),
                "historical_mean_return_annual": float(np.mean(returns) * 252)
            },
            "recommendations": self._generate_simulation_recommendations(gbm_result, stress_result)
        }

    def _generate_simulation_recommendations(
        self,
        simulation_result: SimulationResult,
        stress_result: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate recommendations based on simulation results"""
        recommendations = []

        # Check VaR
        var_95_pct = simulation_result.risk_metrics["var_95_pct"]
        if var_95_pct > 20:
            recommendations.append({
                "priority": "high",
                "type": "risk",
                "message": f"95% VaR is {var_95_pct:.1f}%. Consider reducing position sizes."
            })
        elif var_95_pct > 10:
            recommendations.append({
                "priority": "medium",
                "type": "risk",
                "message": f"95% VaR is {var_95_pct:.1f}%. Monitor risk exposure."
            })

        # Check probability of profit
        prob_profit = simulation_result.statistics["probability_of_profit"]
        if prob_profit < 40:
            recommendations.append({
                "priority": "high",
                "type": "strategy",
                "message": f"Probability of profit is only {prob_profit:.1f}%. Review strategy."
            })
        elif prob_profit > 70:
            recommendations.append({
                "priority": "low",
                "type": "strategy",
                "message": f"Probability of profit is {prob_profit:.1f}%. Strategy looks favorable."
            })

        # Check stress scenarios
        worst_case = stress_result["worst_case"]
        if worst_case["loss_pct"] > 30:
            recommendations.append({
                "priority": "high",
                "type": "stress",
                "message": f"Worst case scenario shows {worst_case['loss_pct']:.1f}% loss. Ensure adequate capital buffer."
            })

        # Check max drawdown
        max_dd = simulation_result.risk_metrics["max_drawdown_pct"]
        if max_dd > 25:
            recommendations.append({
                "priority": "high",
                "type": "drawdown",
                "message": f"Simulated max drawdown is {max_dd:.1f}%. Consider tighter risk controls."
            })

        if not recommendations:
            recommendations.append({
                "priority": "low",
                "type": "general",
                "message": "Simulation results are within acceptable risk parameters."
            })

        return recommendations


if __name__ == "__main__":
    from database import SessionLocal

    db = SessionLocal()
    simulator = MonteCarloSimulator(db)

    # Test simulation (would need actual data)
    print("Monte Carlo Simulator initialized")
    print("Available methods:")
    for method in SimulationMethod:
        print(f"  - {method.value}")

    db.close()
