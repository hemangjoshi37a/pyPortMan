"""
Portfolio Rebalancing Manager for pyPortMan
Handles portfolio rebalancing based on target allocations
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

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


class RebalancingManager:
    """Manager for portfolio rebalancing operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_current_allocation(self, account_id: int) -> Dict[str, Any]:
        """
        Get current portfolio allocation by stock
        Returns dict with stock-wise allocation percentages
        """
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

        total_value = sum(h.current_value for h in holdings)

        allocation = {}
        for holding in holdings:
            allocation[holding.stock] = {
                "value": holding.current_value,
                "percentage": (holding.current_value / total_value * 100) if total_value > 0 else 0,
                "quantity": holding.qty,
                "avg_price": holding.avg_price,
                "ltp": holding.ltp
            }

        return {
            "total_value": total_value,
            "allocation": allocation,
            "stocks_count": len(holdings)
        }

    def calculate_rebalance_trades(
        self,
        account_id: int,
        target_allocations: Dict[str, float],
        total_portfolio_value: Optional[float] = None,
        min_trade_amount: float = 1000,
        max_trade_amount: Optional[float] = None,
        allow_cash_buffer: float = 0.05
    ) -> Dict[str, Any]:
        """
        Calculate required trades to rebalance portfolio to target allocations

        Args:
            account_id: Account ID
            target_allocations: Dict of {stock: target_percentage} (e.g., {"RELIANCE": 20, "TCS": 15})
            total_portfolio_value: Optional total value to use (defaults to current portfolio value)
            min_trade_amount: Minimum trade amount to avoid tiny trades
            max_trade_amount: Optional maximum trade amount per stock
            allow_cash_buffer: Percentage of portfolio to keep as cash (default 5%)

        Returns:
            Dict with buy/sell suggestions and summary
        """
        # Get current holdings
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

        # Calculate total portfolio value
        if total_portfolio_value is None:
            total_value = sum(h.current_value for h in holdings)
        else:
            total_value = total_portfolio_value

        # Calculate investable amount (minus cash buffer)
        investable_amount = total_value * (1 - allow_cash_buffer)

        # Calculate current allocations
        current_allocations = {}
        for holding in holdings:
            current_allocations[holding.stock] = {
                "value": holding.current_value,
                "percentage": (holding.current_value / total_value * 100) if total_value > 0 else 0,
                "quantity": holding.qty,
                "ltp": holding.ltp
            }

        # Calculate target values and required trades
        buy_trades = []
        sell_trades = []
        trades_summary = {
            "total_buy_value": 0,
            "total_sell_value": 0,
            "net_cash_flow": 0,
            "stocks_to_buy": 0,
            "stocks_to_sell": 0,
            "stocks_to_hold": 0
        }

        # Process all stocks in target allocations
        for stock, target_pct in target_allocations.items():
            target_value = investable_amount * (target_pct / 100)

            if stock in current_allocations:
                current_value = current_allocations[stock]["value"]
                current_pct = current_allocations[stock]["percentage"]
                ltp = current_allocations[stock]["ltp"]
                current_qty = current_allocations[stock]["quantity"]

                # Calculate difference
                value_diff = target_value - current_value
                pct_diff = target_pct - current_pct

                if abs(value_diff) < min_trade_amount:
                    # Trade too small, skip
                    trades_summary["stocks_to_hold"] += 1
                    continue

                if value_diff > 0:
                    # Need to buy
                    qty_to_buy = int(value_diff / ltp)
                    trade_value = qty_to_buy * ltp

                    # Apply max trade amount limit
                    if max_trade_amount and trade_value > max_trade_amount:
                        qty_to_buy = int(max_trade_amount / ltp)
                        trade_value = qty_to_buy * ltp

                    if qty_to_buy > 0:
                        buy_trades.append({
                            "stock": stock,
                            "action": "BUY",
                            "quantity": qty_to_buy,
                            "price": ltp,
                            "trade_value": trade_value,
                            "current_value": current_value,
                            "target_value": target_value,
                            "current_pct": round(current_pct, 2),
                            "target_pct": target_pct,
                            "pct_diff": round(pct_diff, 2)
                        })
                        trades_summary["total_buy_value"] += trade_value
                        trades_summary["stocks_to_buy"] += 1
                else:
                    # Need to sell
                    qty_to_sell = int(abs(value_diff) / ltp)
                    # Don't sell more than we have
                    qty_to_sell = min(qty_to_sell, current_qty)
                    trade_value = qty_to_sell * ltp

                    if qty_to_sell > 0:
                        sell_trades.append({
                            "stock": stock,
                            "action": "SELL",
                            "quantity": qty_to_sell,
                            "price": ltp,
                            "trade_value": trade_value,
                            "current_value": current_value,
                            "target_value": target_value,
                            "current_pct": round(current_pct, 2),
                            "target_pct": target_pct,
                            "pct_diff": round(pct_diff, 2)
                        })
                        trades_summary["total_sell_value"] += trade_value
                        trades_summary["stocks_to_sell"] += 1
            else:
                # New stock to add
                # Need to get current price for new stock
                target_value = investable_amount * (target_pct / 100)

                if target_value >= min_trade_amount:
                    # For new stocks, we'll need to fetch the price
                    # This is a placeholder - in real implementation, you'd fetch from Kite
                    buy_trades.append({
                        "stock": stock,
                        "action": "BUY",
                        "quantity": 0,  # Will be calculated when price is known
                        "price": 0,  # Will be fetched
                        "trade_value": target_value,
                        "current_value": 0,
                        "target_value": target_value,
                        "current_pct": 0,
                        "target_pct": target_pct,
                        "pct_diff": target_pct,
                        "is_new_stock": True
                    })
                    trades_summary["total_buy_value"] += target_value
                    trades_summary["stocks_to_buy"] += 1

        # Calculate net cash flow
        trades_summary["net_cash_flow"] = trades_summary["total_sell_value"] - trades_summary["total_buy_value"]

        # Calculate drift (how far from target)
        total_drift = sum(abs(t.get("pct_diff", 0)) for t in buy_trades + sell_trades)
        avg_drift = total_drift / len(target_allocations) if target_allocations else 0

        return {
            "account_id": account_id,
            "total_portfolio_value": total_value,
            "investable_amount": investable_amount,
            "cash_buffer": total_value * allow_cash_buffer,
            "current_allocation": current_allocations,
            "target_allocation": target_allocations,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "summary": trades_summary,
            "drift_analysis": {
                "total_drift": round(total_drift, 2),
                "avg_drift": round(avg_drift, 2),
                "needs_rebalancing": total_drift > 10  # Rebalance if total drift > 10%
            },
            "calculated_at": datetime.utcnow().isoformat()
        }

    def get_rebalancing_summary(self, account_id: int) -> Dict[str, Any]:
        """
        Get a summary of current portfolio and rebalancing needs
        """
        current = self.get_current_allocation(account_id)

        # Calculate concentration risk
        allocations = current["allocation"]
        sorted_allocations = sorted(allocations.items(), key=lambda x: x[1]["percentage"], reverse=True)

        # Top 3 holdings concentration
        top_3_concentration = sum(v["percentage"] for _, v in sorted_allocations[:3])

        # Herfindahl index (concentration measure)
        herfindahl = sum((v["percentage"] / 100) ** 2 for _, v in allocations.values())

        # Diversification score (inverse of concentration)
        diversification_score = (1 - herfindahl) * 100

        return {
            "account_id": account_id,
            "total_value": current["total_value"],
            "stocks_count": current["stocks_count"],
            "top_holdings": [
                {
                    "stock": stock,
                    "value": data["value"],
                    "percentage": round(data["percentage"], 2)
                }
                for stock, data in sorted_allocations[:5]
            ],
            "concentration_metrics": {
                "top_3_concentration": round(top_3_concentration, 2),
                "top_5_concentration": round(sum(v["percentage"] for _, v in sorted_allocations[:5]), 2),
                "herfindahl_index": round(herfindahl, 4),
                "diversification_score": round(diversification_score, 2)
            },
            "risk_assessment": {
                "highly_concentrated": top_3_concentration > 50,
                "well_diversified": diversification_score > 70,
                "needs_diversification": diversification_score < 50
            },
            "calculated_at": datetime.utcnow().isoformat()
        }

    def suggest_target_allocation(
        self,
        account_id: int,
        strategy: str = "equal_weight",
        max_stocks: int = 10,
        min_allocation: float = 5.0
    ) -> Dict[str, Any]:
        """
        Suggest target allocations based on different strategies

        Args:
            account_id: Account ID
            strategy: "equal_weight", "value_weighted", "risk_parity"
            max_stocks: Maximum number of stocks to include
            min_allocation: Minimum allocation percentage per stock

        Returns:
            Dict with suggested target allocations
        """
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

        if not holdings:
            return {"error": "No holdings found"}

        # Sort holdings by current value
        sorted_holdings = sorted(holdings, key=lambda h: h.current_value, reverse=True)
        top_holdings = sorted_holdings[:max_stocks]

        target_allocations = {}

        if strategy == "equal_weight":
            # Equal weight for all top stocks
            weight = 100 / len(top_holdings)
            for holding in top_holdings:
                target_allocations[holding.stock] = weight

        elif strategy == "value_weighted":
            # Weight by current value (proportional)
            total_value = sum(h.current_value for h in top_holdings)
            for holding in top_holdings:
                target_allocations[holding.stock] = (holding.current_value / total_value) * 100

        elif strategy == "risk_parity":
            # Simplified risk parity - inverse of volatility (using price range as proxy)
            # In real implementation, use historical volatility
            price_ranges = []
            for holding in top_holdings:
                # Use day high-low as volatility proxy
                volatility = max(holding.day_high - holding.day_low, 1) if hasattr(holding, 'day_high') else holding.ltp * 0.02
                price_ranges.append((holding.stock, volatility))

            # Calculate inverse weights
            total_inverse = sum(1 / v for _, v in price_ranges)
            for stock, volatility in price_ranges:
                target_allocations[stock] = ((1 / volatility) / total_inverse) * 100

        # Filter by minimum allocation
        filtered_allocations = {
            k: v for k, v in target_allocations.items() if v >= min_allocation
        }

        # Renormalize to 100%
        if filtered_allocations:
            total = sum(filtered_allocations.values())
            filtered_allocations = {k: round((v / total) * 100, 2) for k, v in filtered_allocations.items()}

        return {
            "strategy": strategy,
            "max_stocks": max_stocks,
            "min_allocation": min_allocation,
            "target_allocations": filtered_allocations,
            "stocks_included": len(filtered_allocations),
            "excluded_stocks": len(top_holdings) - len(filtered_allocations),
            "calculated_at": datetime.utcnow().isoformat()
        }

    def simulate_rebalance(
        self,
        account_id: int,
        target_allocations: Dict[str, float],
        transaction_cost_pct: float = 0.1
    ) -> Dict[str, Any]:
        """
        Simulate the rebalancing and show post-rebalance portfolio

        Args:
            account_id: Account ID
            target_allocations: Target allocation percentages
            transaction_cost_pct: Transaction cost as percentage

        Returns:
            Dict with pre and post rebalance comparison
        """
        # Get current state
        current = self.get_current_allocation(account_id)

        # Calculate rebalance trades
        rebalance = self.calculate_rebalance_trades(
            account_id,
            target_allocations,
            total_portfolio_value=current["total_value"]
        )

        # Calculate post-rebalance state
        post_allocation = {}
        for stock, data in current["allocation"].items():
            post_allocation[stock] = {
                "value": data["value"],
                "percentage": data["percentage"]
            }

        # Apply buy trades
        for trade in rebalance["buy_trades"]:
            stock = trade["stock"]
            if stock in post_allocation:
                post_allocation[stock]["value"] += trade["trade_value"]
            else:
                post_allocation[stock] = {
                    "value": trade["trade_value"],
                    "percentage": 0
                }

        # Apply sell trades
        for trade in rebalance["sell_trades"]:
            stock = trade["stock"]
            if stock in post_allocation:
                post_allocation[stock]["value"] -= trade["trade_value"]

        # Calculate transaction costs
        total_transaction_cost = (rebalance["summary"]["total_buy_value"] +
                                 rebalance["summary"]["total_sell_value"]) * (transaction_cost_pct / 100)

        # Recalculate percentages
        total_post_value = sum(v["value"] for v in post_allocation.values())
        for stock in post_allocation:
            post_allocation[stock]["percentage"] = (post_allocation[stock]["value"] / total_post_value * 100) if total_post_value > 0 else 0

        # Calculate allocation error (how close to target)
        allocation_errors = {}
        for stock, target_pct in target_allocations.items():
            current_pct = post_allocation.get(stock, {}).get("percentage", 0)
            allocation_errors[stock] = abs(current_pct - target_pct)

        avg_allocation_error = sum(allocation_errors.values()) / len(allocation_errors) if allocation_errors else 0

        return {
            "account_id": account_id,
            "pre_rebalance": {
                "total_value": current["total_value"],
                "allocation": {k: round(v["percentage"], 2) for k, v in current["allocation"].items()}
            },
            "post_rebalance": {
                "total_value": total_post_value,
                "allocation": {k: round(v["percentage"], 2) for k, v in post_allocation.items()},
                "transaction_cost": round(total_transaction_cost, 2)
            },
            "trades": {
                "buy_count": len(rebalance["buy_trades"]),
                "sell_count": len(rebalance["sell_trades"]),
                "total_buy_value": round(rebalance["summary"]["total_buy_value"], 2),
                "total_sell_value": round(rebalance["summary"]["total_sell_value"], 2)
            },
            "allocation_accuracy": {
                "avg_error": round(avg_allocation_error, 2),
                "max_error": round(max(allocation_errors.values()) if allocation_errors else 0, 2),
                "target_achieved": avg_allocation_error < 2
            },
            "calculated_at": datetime.utcnow().isoformat()
        }
