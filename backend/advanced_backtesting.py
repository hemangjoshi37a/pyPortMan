"""
Advanced Backtesting Suite for pyPortMan
Walk-forward analysis, Monte Carlo simulation, and robustness testing
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
import random

from backtesting import Backtester, BacktestConfig, Trade, BacktestResult


class RobustnessTestType(Enum):
    """Types of robustness tests"""
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    PARAMETER_SWEEP = "parameter_sweep"
    NOISE_INJECTION = "noise_injection"
    OUT_OF_SAMPLE = "out_of_sample"
    STRESS_TEST = "stress_test"


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward analysis"""
    in_sample_days: int = 252 * 2  # 2 years default
    out_of_sample_days: int = 63   # 3 months default
    step_size: int = 21            # 1 month steps
    optimization_metric: str = "sharpe_ratio"  # sharpe_ratio, profit_factor, total_pnl


@dataclass
class WalkForwardResult:
    """Results from walk-forward analysis"""
    window_results: List[Dict] = field(default_factory=list)
    overall_metrics: Dict[str, float] = field(default_factory=dict)
    consistency_score: float = 0.0
    parameter_stability: Dict = field(default_factory=dict)
    forward_test_equity: List[float] = field(default_factory=list)
    in_sample_equity: List[float] = field(default_factory=list)
    success_rate: float = 0.0


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation"""
    simulations: int = 1000
    initial_capital: float = 100000
    trades_sample_size: int = 100  # Number of trades to sample for each simulation
    confidence_level: float = 0.95


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation"""
    equity_curves: List[List[float]] = field(default_factory=list)
    final_equities: List[float] = field(default_factory=list)
    return_percentiles: Dict[float, float] = field(default_factory=dict)
    max_drawdowns: List[float] = field(default_factory=list)
    probability_of_ruin: float = 0.0
    expected_return: float = 0.0
    sharpe_ratio: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)


@dataclass
class RobustnessTestResult:
    """Comprehensive robustness test results"""
    test_type: RobustnessTestType
    test_config: Dict
    original_performance: Dict
    perturbed_performance: Dict
    robustness_score: float
    passed_tests: int
    total_tests: int
    worst_case_dr: float
    best_case_dr: float


class WalkForwardAnalyzer:
    """
    Walk-forward analysis implementation
    Validates strategy performance across different market regimes
    """

    def __init__(self, config: WalkForwardConfig):
        self.config = config

    def run_walk_forward(
        self,
        data: pd.DataFrame,
        strategy: Callable,
        strategy_params: Dict[str, Any] = None
    ) -> WalkForwardResult:
        """
        Run walk-forward analysis

        Args:
            data: Historical data with index as dates
            strategy: Strategy function
            strategy_params: Strategy parameters to optimize

        Returns:
            WalkForwardResult object
        """
        if strategy_params is None:
            strategy_params = {}

        # Split data into windows
        windows = self._create_walk_forward_windows(data)

        window_results = []
        all_trades = []
        in_sample_equity = []
        forward_test_equity = []
        successful_windows = 0

        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            logger.info(f"Running walk-forward window {i+1}/{len(windows)}")

            # Prepare training and testing data
            train_data = data[(data.index >= train_start) & (data.index < train_end)]
            test_data = data[(data.index >= test_start) & (data.index < test_end)]

            if len(train_data) < 50 or len(test_data) < 10:
                continue

            # Optimize strategy on training data
            best_params = self._optimize_strategy_params(train_data, strategy, strategy_params)

            # Run strategy on training data with best params
            train_config = BacktestConfig()
            train_backtester = Backtester(train_config)
            train_result = train_backtester.run_backtest(train_data, strategy, best_params)

            # Run strategy forward on test data with same params
            test_config = BacktestConfig()
            test_backtester = Backtester(test_config)
            test_result = test_backtester.run_backtest(test_data, strategy, best_params)

            # Record results
            window_result = {
                "window_index": i,
                "train_start": train_start.isoformat(),
                "train_end": train_end.isoformat(),
                "test_start": test_start.isoformat(),
                "test_end": test_end.isoformat(),
                "train_performance": {
                    "total_trades": train_result.total_trades,
                    "win_rate": train_result.win_rate,
                    "profit_factor": train_result.profit_factor,
                    "sharpe_ratio": train_result.sharpe_ratio,
                    "total_pnl": train_result.total_pnl
                },
                "test_performance": {
                    "total_trades": test_result.total_trades,
                    "win_rate": test_result.win_rate,
                    "profit_factor": test_result.profit_factor,
                    "sharpe_ratio": test_result.sharpe_ratio,
                    "total_pnl": test_result.total_pnl
                },
                "parameter_values": best_params
            }

            # Check if forward test was profitable
            if test_result.total_pnl > 0:
                successful_windows += 1

            window_results.append(window_result)
            all_trades.extend(test_result.trades)
            in_sample_equity.extend(train_result.equity_curve)
            forward_test_equity.extend(test_result.equity_curve)

        # Calculate overall metrics
        overall_metrics = self._calculate_walk_forward_metrics(window_results)
        consistency_score = self._calculate_consistency_score(window_results)
        parameter_stability = self._analyze_parameter_stability(window_results)
        success_rate = successful_windows / len(windows) if windows else 0

        return WalkForwardResult(
            window_results=window_results,
            overall_metrics=overall_metrics,
            consistency_score=consistency_score,
            parameter_stability=parameter_stability,
            forward_test_equity=forward_test_equity,
            in_sample_equity=in_sample_equity,
            success_rate=success_rate
        )

    def _create_walk_forward_windows(self, data: pd.DataFrame) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """Create walk-forward windows"""
        windows = []
        dates = data.index

        if len(dates) < self.config.in_sample_days + self.config.out_of_sample_days:
            return windows

        # Start from first available date + in_sample period
        start_idx = self.config.in_sample_days
        step_size = self.config.step_size

        while start_idx + self.config.out_of_sample_days < len(dates):
            train_start = dates[0] if not windows else windows[-1][2]  # Overlap windows
            train_end = dates[start_idx]
            test_start = dates[start_idx]
            test_end = dates[min(start_idx + self.config.out_of_sample_days, len(dates)-1)]

            windows.append((train_start, train_end, test_start, test_end))

            start_idx += step_size

        return windows

    def _optimize_strategy_params(
        self,
        train_data: pd.DataFrame,
        strategy: Callable,
        param_grid: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """Optimize strategy parameters on training data"""
        best_params = {}
        best_score = float('-inf')

        # Use grid search for parameter optimization
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        # Simple grid search - in production use more sophisticated optimization
        from itertools import product

        for combination in product(*param_values):
            params = dict(zip(param_names, combination))

            try:
                config = BacktestConfig()
                backtester = Backtester(config)
                result = backtester.run_backtest(train_data, strategy, params)

                # Score based on optimization metric
                if self.config.optimization_metric == "sharpe_ratio":
                    score = result.sharpe_ratio
                elif self.config.optimization_metric == "profit_factor":
                    score = result.profit_factor
                elif self.config.optimization_metric == "total_pnl":
                    score = result.total_pnl
                else:
                    score = result.total_pnl  # Default

                if score > best_score:
                    best_score = score
                    best_params = params

            except Exception as e:
                logger.warning(f"Error optimizing parameters {params}: {e}")
                continue

        return best_params if best_params else {}

    def _calculate_walk_forward_metrics(self, window_results: List[Dict]) -> Dict[str, float]:
        """Calculate overall walk-forward metrics"""
        if not window_results:
            return {}

        win_rates = [w["test_performance"]["win_rate"] for w in window_results]
        profit_factors = [w["test_performance"]["profit_factor"] for w in window_results]
        pnls = [w["test_performance"]["total_pnl"] for w in window_results]
        sharpe_ratios = [w["test_performance"]["sharpe_ratio"] for w in window_results]

        return {
            "avg_win_rate": np.mean(win_rates),
            "avg_profit_factor": np.mean(profit_factors),
            "total_pnl": sum(pnls),
            "avg_sharpe_ratio": np.mean(sharpe_ratios),
            "consistency_score": len([w for w in window_results if w["test_performance"]["total_pnl"] > 0]) / len(window_results),
            "std_win_rate": np.std(win_rates),
            "std_profit_factor": np.std(profit_factors)
        }

    def _calculate_consistency_score(self, window_results: List[Dict]) -> float:
        """Calculate consistency score (0-100)"""
        if not window_results:
            return 0.0

        # Score based on:
        # 1. Percentage of profitable windows
        # 2. Standard deviation of performance metrics
        # 3. Parameter stability

        profitable_windows = sum(1 for w in window_results if w["test_performance"]["total_pnl"] > 0)
        profit_rate = profitable_windows / len(window_results)

        # Lower std dev in performance = higher consistency
        pnls = [w["test_performance"]["total_pnl"] for w in window_results]
        if len(pnls) > 1 and np.mean(pnls) != 0:
            consistency_ratio = 1 - (np.std(pnls) / abs(np.mean(pnls)))
        else:
            consistency_ratio = 1.0

        # Parameter stability (lower parameter variation across windows)
        params_windows = []
        for w in window_results:
            if w["parameter_values"]:
                params_windows.append(len(w["parameter_values"]))
        param_stability = 1.0 if not params_windows else (1.0 - np.std(params_windows))

        # Weighted average
        score = (profit_rate * 0.5 + consistency_ratio * 0.3 + param_stability * 0.2) * 100

        return max(0, min(100, score))

    def _analyze_parameter_stability(self, window_results: List[Dict]) -> Dict[str, Any]:
        """Analyze how stable parameters are across windows"""
        if not window_results:
            return {}

        # Collect all parameters used
        all_params = {}
        for window in window_results:
            params = window.get("parameter_values", {})
            for key, value in params.items():
                if key not in all_params:
                    all_params[key] = []
                all_params[key].append(value)

        # Calculate stability metrics for each parameter
        stability = {}
        for param, values in all_params.items():
            if len(values) > 1:
                stability[param] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "cv": np.std(values) / np.mean(values) if np.mean(values) != 0 else 0,
                    "values": values
                }

        return stability


class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy robustness testing
    """

    def __init__(self, config: MonteCarloConfig):
        self.config = config

    def run_monte_carlo(
        self,
        backtest_result: BacktestResult,
        strategy_size: int = 100
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation on backtest results

        Args:
            backtest_result: Original backtest results
            strategy_size: Number of trades per simulation
        Returns:
            MonteCarloResult object
        """
        # Extract trade data
        trades_data = self._extract_trades_data(backtest_result.trades)

        if not trades_data:
            return MonteCarloResult()

        # Run simulations
        equity_curves = []
        final_equities = []
        max_drawdowns = []

        for sim in range(self.config.simulations):
            # Run one simulation
            equity_curve = self._run_single_simulation(
                trades_data,
                self.config.initial_capital,
                strategy_size
            )

            final_equity = equity_curve[-1]
            max_dd = self._calculate_max_drawdown(equity_curve)

            equity_curves.append(equity_curve)
            final_equities.append(final_equity)
            max_drawdowns.append(max_dd)

        # Calculate statistics
        return_percentiles = self._calculate_percentiles(final_equities, [0.1, 0.25, 0.5, 0.75, 0.9])

        # Probability of ruin (losing more than 50%)
        probability_of_ruin = sum(1 for eq in final_equities if eq < self.config.initial_capital * 0.5)
        probability_of_ruin /= len(final_equities)

        # Performance metrics
        expected_return = np.mean(final_equities)
        sharpe_ratio = self._calculate_portfolio_sharpe(final_equities)

        # Confidence interval
        ci_lower = np.percentile(final_equities, (1 - self.config.confidence_level) / 2 * 100)
        ci_upper = np.percentile(final_equities, (1 + self.config.confidence_level) / 2 * 100)

        return MonteCarloResult(
            equity_curves=equity_curves[:10],  # Store first 10 for visualization
            final_equities=final_equities,
            return_percentiles=return_percentiles,
            max_drawdowns=max_drawdowns,
            probability_of_ruin=probability_of_ruin,
            expected_return=expected_return,
            sharpe_ratio=sharpe_ratio,
            confidence_interval=(ci_lower, ci_upper)
        )

    def _extract_trades_data(self, trades: List[Trade]) -> List[Dict[str, float]]:
        """Extract trade data for Monte Carlo simulation"""
        trades_data = []

        for trade in trades:
            trades_data.append({
                "return_pct": trade.pnl_percent,
                "holding_days": trade.holding_period_days,
                "pnl": trade.pnl
            })

        return trades_data

    def _run_single_simulation(
        self,
        trades_data: List[Dict],
        initial_capital: float,
        sample_size: int
    ) -> List[float]:
        """Run a single Monte Carlo simulation"""
        capital = initial_capital
        equity_curve = [capital]

        for _ in range(sample_size):
            # Sample a random trade from historical data
            random_trade = random.choice(trades_data)

            # Apply the trade
            pnl_pct = random_trade["return_pct"]
            trade_pnl = capital * (pnl_pct / 100)
            capital += trade_pnl

            equity_curve.append(capital)

            # Stop if capital falls too low
            if capital < initial_capital * 0.01:
                break

        return equity_curve

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown from equity curve"""
        if not equity_curve:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_percentiles(self, values: List[float], percentiles: List[float]) -> Dict[float, float]:
        """Calculate percentiles"""
        results = {}
        for p in percentiles:
            results[p] = np.percentile(values, p * 100)
        return results

    def _calculate_portfolio_sharpe(self, final_equities: List[float]) -> float:
        """Calculate Sharpe ratio from final equities"""
        if len(final_equities) < 2:
            return 0.0

        returns = []
        for i in range(1, len(final_equities)):
            equity_prev, equity_curr = final_equities[i-1], final_equities[i]
            if equity_prev > 0:
                returns.append((equity_curr - equity_prev) / equity_prev)

        if not returns:
            return 0.0

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return > 0:
            return avg_return / std_return * np.sqrt(252)

        return 0.0


class RobustnessTester:
    """
    Comprehensive robustness testing framework
    """

    def __init__(self):
        self.test_results = []

    def run_robustness_test(
        self,
        original_result: BacktestResult,
        data: pd.DataFrame,
        strategy: Callable,
        test_types: List[RobustnessTestType]
    ) -> List[Ro
