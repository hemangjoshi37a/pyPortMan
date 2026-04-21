"""
Order Execution Monitoring Module for pyPortMan
Tracks order execution quality, slippage, and provides execution analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

from sqlalchemy.orm import Session
from kiteconnect import KiteConnect

from models import Order, Account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('execution_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Order execution metrics"""
    order_id: str
    symbol: str
    order_type: str
    transaction_type: str
    requested_price: float
    execution_price: float
    quantity: int
    slippage: float
    slippage_pct: float
    execution_time: datetime
    delay_seconds: float
    estimated_cost: float
    market_impact: float
    liquidity_score: float
    execution_quality: str


@dataclass
class ExecutionSummary:
    """Summary of execution statistics"""
    total_orders: int
    total_quantity: int
    total_value: float
    average_slippage_pct: float
    best_execution_pct: float
    worst_execution_pct: float
    slippage_std: float
    execution_success_rate: float
    average_delay_seconds: float
    total_slippage_cost: float
    execution_quality_rating: str


class OrderExecutionMonitor:
    """
    Monitor order execution quality, slippage, and provide execution analytics
    """

    def __init__(self, db: Session, kite: Optional[KiteConnect] = None):
        self.db = db
        self.kite = kite
        self.execution_history: List[ExecutionMetrics] = []

    def track_order_execution(self, order: Order, market_data: Dict[str, float]) -> ExecutionMetrics:
        """
        Track individual order execution details

        Args:
            order: Executed order from database
            market_data: Market data at time of order placement

        Returns:
            ExecutionMetrics object
        """
        # Calculate slippage
        requested_price = order.price
        execution_price = self._get_execution_price(order, market_data)
        slippage = abs(execution_price - requested_price)
        slippage_pct = (slippage / requested_price * 100) if requested_price > 0 else 0

        # Calculate delay
        delay_seconds = self._calculate_execution_delay(order)

        # Estimate market impact (simplified)
        # Assume 10% of slippage is due to market impact
        market_impact = slippage_pct * 0.1

        # Calculate liquidity score based on order price vs market
        liquidity_score = self._calculate_liquidity_score(order, market_data, slippage_pct)

        # Determine execution quality
        execution_quality = self._rate_execution_quality(slippage_pct, delay_seconds, liquidity_score)

        # Calculate estimated cost of slippage
        estimated_cost = slippage * order.qty

        metrics = ExecutionMetrics(
            order_id=order.order_id,
            symbol=order.stock,
            order_type=order.order_type,
            transaction_type=order.transaction_type,
            requested_price=requested_price,
            execution_price=execution_price,
            quantity=order.qty,
            slippage=slippage,
            slippage_pct=slippage_pct,
            execution_time=order.placed_at,
            delay_seconds=delay_seconds,
            estimated_cost=estimated_cost,
            market_impact=market_impact,
            liquidity_score=liquidity_score,
            execution_quality=execution_quality
        )

        # Store in history
        self.execution_history.append(metrics)

        return metrics

    def _get_execution_price(self, order: Order, market_data: Dict[str, float]) -> float:
        """Get actual execution price from market data or order"""
        # In production, this would fetch from KiteConnect
        # For now, simulate with some slippage
        if order.order_type == "MARKET":
            return market_data.get("last_price", order.price)
        elif order.order_type == "LIMIT":
            return order.price
        else:
            return market_data.get("last_price", order.price)

    def _calculate_execution_delay(self, order: Order) -> float:
        """Calculate execution delay in seconds"""
        # Assume order was placed at order.placed_at
        # and executed at order.updated_at (if available)
        if order.updated_at and order.placed_at:
            delay = (order.updated_at - order.placed_at).total_seconds()
            return max(0, delay)

        # Default delay estimation based on order type
        delays = {
            "MARKET": 1.5,    # Fastest
            "LIMIT": 5.0,     # Can take longer
            "SL": 3.0,        # Stop-loss
            "SL-M": 2.0       # Stop-loss market
        }

        return delays.get(order.order_type, 3.0)

    def _calculate_liquidity_score(self, order: Order, market_data: Dict[str, float], slippage_pct: float) -> float:
        """
        Calculate liquidity score (0-100, higher is better)

        Args:
            order: Order details
            market_data: Market data including OHLCV
            slippage_pct: Calculated slippage percentage

        Returns:
            Liquidity score from 0-100
        """
        score = 100.0

        # Deduct points for high slippage
        if slippage_pct > 2.0:
            score -= 30
        elif slippage_pct > 1.0:
            score -= 15
        elif slippage_pct > 0.5:
            score -= 5

        # Check volume relative to order size
        avg_volume = market_data.get("average_volume", 1000000)
        order_value = order.price * order.qty

        # Normalize volume score
        volume_ratio = order_value / max(avg_volume, 1)
        if volume_ratio > 0.05:  # More than 5% of avg volume
            score -= 20
        elif volume_ratio > 0.02:
            score -= 10

        # Relative to other stocks
        vwap = market_data.get("vwap", order.price)
        vwap_deviation = abs(order.price - vwap) / max(vwap, 1)
        if vwap_deviation > 0.02:
            score -= 10

        return max(0.0, min(100.0, score))

    def _rate_execution_quality(self, slippage_pct: float, delay_seconds: float, liquidity_score: float) -> str:
        """Rate execution quality based on multiple factors"""
        # Weights: 50% slippage, 30% delay, 20% liquidity
        slippage_grade = max(0, 100 - slippage_pct * 10)
        delay_grade = max(0, 100 - delay_seconds * 10)
        liquidity_grade = liquidity_score

        overall_score = (slippage_grade * 0.5 + delay_grade * 0.3 + liquidity_grade * 0.2)

        if overall_score >= 90:
            return "Excellent"
        elif overall_score >= 75:
            return "Good"
        elif overall_score >= 60:
            return "Fair"
        elif overall_score >= 40:
            return "Poor"
        else:
            return "Very Poor"

    def get_execution_summary(self, account_id: Optional[int] = None, days: int = 30) -> ExecutionSummary:
        """
        Get execution summary for account

        Args:
            account_id: Account ID (None for all accounts)
            days: Number of days to analyze

        Returns:
            ExecutionSummary object
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(Order).filter(
            Order.placed_at >= cutoff_date,
            Order.status == "COMPLETE"
        )

        if account_id:
            query = query.filter(Order.account_id == account_id)

        orders = query.all()

        if not orders:
            return ExecutionSummary(
                total_orders=0,
                total_quantity=0,
                total_value=0.0,
                average_slippage_pct=0.0,
                best_execution_pct=0.0,
                worst_execution_pct=0.0,
                slippage_std=0.0,
                execution_success_rate=0.0,
                average_delay_seconds=0.0,
                total_slippage_cost=0.0,
                execution_quality_rating="N/A"
            )

        # Calculate metrics
        total_orders = len(orders)
        slippages = []
        delays = []
        total_quantity = sum(order.qty for order in orders)
        total_value = sum(order.price * order.qty for order in orders)
        total_slippage_cost = 0.0

        for order in orders:
            # Calculate slippage for each order
            market_data = self._get_market_data_at_execution(order)
            metrics = self.track_order_execution(order, market_data)

            slippages.append(metrics.slippage_pct)
            delays.append(metrics.delay_seconds)
            total_slippage_cost += metrics.estimated_cost

        # Summary statistics
        average_slippage = np.mean(slippages) if slippages else 0
        slippage_std = np.std(slippages) if slippages else 0
        best_execution = min(slippages) if slippages else 0
        worst_execution = max(slippages) if slippages else 0
        average_delay = np.mean(delays) if delays else 0

        # Success rate (assuming all completed orders are successful)
        execution_success_rate = 100.0

        # Overall quality rating
        quality_rating = self._calculate_overall_quality(average_slippage, average_delay)

        return ExecutionSummary(
            total_orders=total_orders,
            total_quantity=total_quantity,
            total_value=total_value,
            average_slippage_pct=average_slippage,
            best_execution_pct=best_execution,
            worst_execution_pct=worst_execution,
            slippage_std=slippage_std,
            execution_success_rate=execution_success_rate,
            average_delay_seconds=average_delay,
            total_slippage_cost=total_slippage_cost,
            execution_quality_rating=quality_rating
        )

    def _get_market_data_at_execution(self, order: Order) -> Dict[str, float]:
        """Get market data at time of order execution"""
        # In production, this would fetch historical market data
        # For now, return realistic mock data
        return {
            "last_price": order.price,
            "open": order.price * 0.98,
            "high": order.price * 1.02,
            "low": order.price * 0.97,
            "vwap": order.price * 0.99,
            "average_volume": 500000,  # Typical average volume
            "volume": 100000             # Current day's volume
        }

    def _calculate_overall_quality(self, avg_slippage: float, avg_delay: float) -> str:
        """Calculate overall execution quality rating"""
        slippage_score = max(0, 100 - avg_slippage * 10)
        delay_score = max(0, 100 - avg_delay * 5)

        overall_score = (slippage_score + delay_score) / 2

        if overall_score >= 90:
            return "Excellent"
        elif overall_score >= 80:
            return "Very Good"
        elif overall_score >= 70:
            return "Good"
        elif overall_score >= 60:
            return "Fair"
        else:
            return "Poor"

    def get_slippage_report(self, account_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed slippage report

        Args:
            account_id: Account ID
            days: Number of days to analyze

        Returns:
            Detailed slippage analysis
        """
        summary = self.get_execution_summary(account_id, days)

        # Categorize by order type
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        orders = self.db.query(Order).filter(
            Order.placed_at >= cutoff_date,
            Order.status == "COMPLETE"
        ).all()

        order_type_stats = {}
        for order in orders:
            order_type = order.order_type
            market_data = self._get_market_data_at_execution(order)
            metrics = self.track_order_execution(order, market_data)

            if order_type not in order_type_stats:
                order_type_stats[order_type] = {
                    "count": 0,
                    "total_slippage": 0.0,
                    "slippages": []
                }

            order_type_stats[order_type]["count"] += 1
            order_type_stats[order_type]["total_slippage"] += metrics.slippage_pct
            order_type_stats[order_type]["slippages"].append(metrics.slippage_pct)

        # Calculate statistics by order type
        for order_type, stats in order_type_stats.items():
            if stats["count"] > 0:
                stats["avg_slippage"] = stats["total_slippage"] / stats["count"]
                stats["min_slippage"] = min(stats["slippages"])
                stats["max_slippage"] = max(stats["slippages"])
                stats["std_slippage"] = np.std(stats["slippages"])

        # Time-based analysis
        time_analysis = self._analyze_execution_timing(orders)

        return {
            "summary": summary.__dict__,
            "by_order_type": order_type_stats,
            "by_time": time_analysis,
            "slippage_cost_analysis": {
                "total_cost": summary.total_slippage_cost,
                "cost_per_order": summary.total_slippage_cost / summary.total_orders if summary.total_orders > 0 else 0,
                "cost_per_share": summary.total_slippage_cost / summary.total_quantity if summary.total_quantity > 0 else 0
            },
            "impact_on_performance": self._estimate_performance_impact(summary),
            "recommendations": self._generate_execution_recommendations(order_type_stats, summary)
        }

    def _analyze_execution_timing(self, orders: List[Order]) -> Dict[str, Any]:
        """Analyze execution quality by time of day"""
        # Extract hour from order placed time
        hour_stats = {}
        for order in orders:
            hour = order.placed_at.hour

            if hour not in hour_stats:
                hour_stats[hour] = {
                    "count": 0,
                    "total_slippage": 0.0
                }

            hour_stats[hour]["count"] += 1
            market_data = self._get_market_data_at_execution(order)
            metrics = self.track_order_execution(order, market_data)
            hour_stats[hour]["total_slippage"] += metrics.slippage_pct

        # Calculate averages
        for hour, stats in hour_stats.items():
            if stats["count"] > 0:
                stats["avg_slippage"] = stats["total_slippage"] / stats["count"]

        # Find best and worst hours
        sorted_hours = sorted(hour_stats.items(), key=lambda x: x[1]["avg_slippage"])

        best_hour = None
        worst_hour = None

        if sorted_hours:
            best_hour = {"hour": sorted_hours[0][0], **sorted_hours[0][1]}
            worst_hour = {"hour": sorted_hours[-1][0], **sorted_hours[-1][1]}

        morning_session = sum(1 for order in orders if 9 <= order.placed_at.hour < 12)
        afternoon_session = sum(1 for order in orders if 12 <= order.placed_at.hour < 15)
        closing_session = sum(1 for order in orders if 15 <= order.placed_at.hour < 16)

        return {
            "hourly_breakdown": hour_stats,
            "best_hour": best_hour,
            "worst_hour": worst_hour,
            "session_summary": {
                "morning": morning_session,
                "afternoon": afternoon_session,
                "closing": closing_session
            }
        }

    def _estimate_performance_impact(self, summary: ExecutionSummary) -> Dict[str, float]:
        """Estimate impact on portfolio performance"""
        # Assuming average position holding period of 5 days
        annual_turnover = summary.total_value * (252 / 5)
        annual_slippage_cost = summary.average_slippage_pct / 100 * annual_turnover

        # Impact on returns depends on total capital
        # This is a simplified calculation
        return {
            "annual_slippage_cost": annual_slippage_cost,
            "cost_per_dollar_traded": summary.average_slippage_pct / 100,
            "breakeven_improvement_needed": summary.average_slippage_pct  # To breakeven, need this much improvement
        }

    def _generate_execution_recommendations(self, order_type_stats: Dict, summary: ExecutionSummary) -> List[Dict[str, str]]:
        """Generate recommendations for improving execution quality"""
        recommendations = []

        # Compare order types
        market_slippage = order_type_stats.get("MARKET", {}).get("avg_slippage", 0)
        limit_slippage = order_type_stats.get("LIMIT", {}).get("avg_slippage", summary.average_slippage_pct)

        if market_slippage > 0.5:
            recommendations.append({
                "priority": "high",
                "action": "avoid_market_orders",
                "message": "Market orders have high slippage. Consider using limit orders instead."
            })

        if summary.average_delay_seconds > 3.0:
            recommendations.append({
                "priority": "medium",
                "action": "check_infrastructure",
                "message": "High execution delays. Check network/tech infrastructure."
            })

        # Time-based recommendations
        hour_slippages = self._analyze_execution_timing([])  # Empty for now
        if hour_slippages.get("worst_hour"):
            worst_hour = hour_slippages["worst_hour"]["hour"]
            recommendations.append({
                "priority": "low",
                "action": "avoid_poor_liquidity_hours",
                "message": f"Avoid trading during hour {worst_hour} due to poor liquidity."
            })

        return recommendations

    def get_execution_recommendations(self, account_id: Optional[int] = None) -> List[Dict[str, str]]:
        """Get personalized execution recommendations"""
        summary = self.get_execution_summary(account_id, 30)
        recommendations = []

        if summary.average_slippage_pct > 0.5:
            recommendations.append({
                "priority": "high",
                "action": "optimize_order_types",
                "message": f"High slippage detected ({summary.average_slippage_pct:.2f}%). Review order placement strategy."
            })

        if summary.slippage_std > summary.average_slippage_pct:
            recommendations.append({
                "priority": "medium",
                "action": "reduce_variance",
                "message": "Inconsistent execution quality. Standardize order parameters."
            })

        return recommendations

    def cleanup_old_execution_data(self, days_to_keep: int = 90):
        """Clean up old execution data to manage memory"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        self.execution_history = [
            entry for entry in self.execution_history
            if entry.execution_time >= cutoff_date
        ]
        logger.info(f"Cleaned up execution data older than {days_to_keep} days")


if __name__ == "__main__":
    from database import SessionLocal

    db = SessionLocal()
    monitor = OrderExecutionMonitor(db)

    # Test execution summary
    summary = monitor.get_execution_summary()
    print(f"Total orders tracked: {summary.total_orders}")
    print(f"Average slippage: {summary.average_slippage_pct:.2f}%")
    print(f"Execution quality: {summary.execution_quality_rating}")

    db.close()
