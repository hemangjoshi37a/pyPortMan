"""
Order Book Depth Manager for pyPortMan
View market depth for better entry/exit decisions
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import OrderBookDepth
from kite_manager import KiteManager

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


class OrderBookDepthManager:
    """Manager for order book depth data"""

    def __init__(self, db: Session):
        self.db = db
        self.kite_manager = KiteManager(db)

    def fetch_order_book_depth(
        self,
        account_id: int,
        stock: str,
        exchange: str = "NSE"
    ) -> Dict[str, Any]:
        """
        Fetch current order book depth for a stock
        """
        kite = self.kite_manager.get_kite(account_id)
        if not kite:
            raise ValueError("KiteConnect instance not available")

        try:
            # Get quote data which includes order book depth
            quote = kite.quote(f"{exchange}:{stock}")
            quote_key = f"{exchange}:{stock}"
            quote_data = quote.get(quote_key, {})

            # Extract depth data
            depth = quote_data.get("depth", {})
            buy = depth.get("buy", [])
            sell = depth.get("sell", [])

            # Format bid data (buy orders)
            bid_data = {}
            total_bid_qty = 0
            for i in range(min(5, len(buy))):
                bid_data[f"bid_price_{i+1}"] = buy[i].get("price", 0)
                bid_data[f"bid_qty_{i+1}"] = buy[i].get("quantity", 0)
                total_bid_qty += buy[i].get("quantity", 0)

            # Format ask data (sell orders)
            ask_data = {}
            total_ask_qty = 0
            for i in range(min(5, len(sell))):
                ask_data[f"ask_price_{i+1}"] = sell[i].get("price", 0)
                ask_data[f"ask_qty_{i+1}"] = sell[i].get("quantity", 0)
                total_ask_qty += sell[i].get("quantity", 0)

            # Calculate spread
            best_bid = bid_data.get("bid_price_1", 0)
            best_ask = ask_data.get("ask_price_1", 0)
            spread = best_ask - best_bid if best_ask > 0 and best_bid > 0 else 0
            spread_pct = (spread / best_bid * 100) if best_bid > 0 else 0

            # Combine all data
            order_book_data = {
                "stock": stock,
                "exchange": exchange,
                "last_price": quote_data.get("last_price", 0),
                "timestamp": datetime.utcnow().isoformat(),
                **bid_data,
                **ask_data,
                "total_bid_qty": total_bid_qty,
                "total_ask_qty": total_ask_qty,
                "spread": spread,
                "spread_pct": spread_pct
            }

            # Save to database
            self._save_order_book_depth(order_book_data)

            return order_book_data

        except Exception as e:
            logger.error(f"Error fetching order book depth for {stock}: {e}")
            raise

    def _save_order_book_depth(self, data: Dict[str, Any]) -> OrderBookDepth:
        """
        Save order book depth data to database
        """
        order_book = OrderBookDepth(
            stock=data["stock"],
            exchange=data["exchange"],
            recorded_at=datetime.utcnow(),
            bid_price_1=data.get("bid_price_1"),
            bid_qty_1=data.get("bid_qty_1"),
            bid_price_2=data.get("bid_price_2"),
            bid_qty_2=data.get("bid_qty_2"),
            bid_price_3=data.get("bid_price_3"),
            bid_qty_3=data.get("bid_qty_3"),
            bid_price_4=data.get("bid_price_4"),
            bid_qty_4=data.get("bid_qty_4"),
            bid_price_5=data.get("bid_price_5"),
            bid_qty_5=data.get("bid_qty_5"),
            ask_price_1=data.get("ask_price_1"),
            ask_qty_1=data.get("ask_qty_1"),
            ask_price_2=data.get("ask_price_2"),
            ask_qty_2=data.get("ask_qty_2"),
            ask_price_3=data.get("ask_price_3"),
            ask_qty_3=data.get("ask_qty_3"),
            ask_price_4=data.get("ask_price_4"),
            ask_qty_4=data.get("ask_qty_4"),
            ask_price_5=data.get("ask_price_5"),
            ask_qty_5=data.get("ask_qty_5"),
            total_bid_qty=data.get("total_bid_qty", 0),
            total_ask_qty=data.get("total_ask_qty", 0),
            spread=data.get("spread", 0),
            spread_pct=data.get("spread_pct", 0)
        )

        self.db.add(order_book)
        self.db.commit()

        return order_book

    def get_historical_depth(
        self,
        stock: str,
        limit: int = 100
    ) -> List[OrderBookDepth]:
        """
        Get historical order book depth data for a stock
        """
        return self.db.query(OrderBookDepth).filter(
            OrderBookDepth.stock == stock
        ).order_by(
            OrderBookDepth.recorded_at.desc()
        ).limit(limit).all()

    def analyze_order_book(self, stock: str) -> Dict[str, Any]:
        """
        Analyze order book depth and provide insights
        """
        # Get latest order book data
        latest = self.db.query(OrderBookDepth).filter(
            OrderBookDepth.stock == stock
        ).order_by(
            OrderBookDepth.recorded_at.desc()
        ).first()

        if not latest:
            raise ValueError(f"No order book data found for {stock}")

        # Calculate buy/sell ratio
        buy_sell_ratio = latest.total_bid_qty / latest.total_ask_qty if latest.total_ask_qty > 0 else 0

        # Calculate weighted average prices
        bid_weighted_price = self._calculate_weighted_price([
            (latest.bid_price_1, latest.bid_qty_1),
            (latest.bid_price_2, latest.bid_qty_2),
            (latest.bid_price_3, latest.bid_qty_3),
            (latest.bid_price_4, latest.bid_qty_4),
            (latest.bid_price_5, latest.bid_qty_5)
        ])

        ask_weighted_price = self._calculate_weighted_price([
            (latest.ask_price_1, latest.ask_qty_1),
            (latest.ask_price_2, latest.ask_qty_2),
            (latest.ask_price_3, latest.ask_qty_3),
            (latest.ask_price_4, latest.ask_qty_4),
            (latest.ask_price_5, latest.ask_qty_5)
        ])

        # Determine market sentiment
        sentiment = "NEUTRAL"
        if buy_sell_ratio > 1.5:
            sentiment = "BULLISH"
        elif buy_sell_ratio < 0.67:
            sentiment = "BEARISH"

        # Calculate liquidity score
        total_liquidity = latest.total_bid_qty + latest.total_ask_qty
        liquidity_score = min(100, total_liquidity / 10000)  # Normalize to 0-100

        return {
            "stock": stock,
            "buy_sell_ratio": buy_sell_ratio,
            "sentiment": sentiment,
            "bid_weighted_price": bid_weighted_price,
            "ask_weighted_price": ask_weighted_price,
            "spread": latest.spread,
            "spread_pct": latest.spread_pct,
            "total_liquidity": total_liquidity,
            "liquidity_score": liquidity_score,
            "timestamp": latest.recorded_at.isoformat()
        }

    def _calculate_weighted_price(self, price_qty_pairs: List[tuple]) -> float:
        """
        Calculate weighted average price from price-quantity pairs
        """
        total_qty = sum(qty for price, qty in price_qty_pairs if qty)
        if total_qty == 0:
            return 0

        weighted_sum = sum(price * qty for price, qty in price_qty_pairs if qty)
        return weighted_sum / total_qty

    def get_order_book_summary(self, stocks: List[str]) -> Dict[str, Any]:
        """
        Get order book summary for multiple stocks
        """
        summary = {}

        for stock in stocks:
            try:
                latest = self.db.query(OrderBookDepth).filter(
                    OrderBookDepth.stock == stock
                ).order_by(
                    OrderBookDepth.recorded_at.desc()
                ).first()

                if latest:
                    summary[stock] = {
                        "last_price": latest.bid_price_1,  # Using bid as proxy
                        "spread": latest.spread,
                        "spread_pct": latest.spread_pct,
                        "total_bid_qty": latest.total_bid_qty,
                        "total_ask_qty": latest.total_ask_qty,
                        "timestamp": latest.recorded_at.isoformat()
                    }
            except Exception as e:
                logger.error(f"Error getting summary for {stock}: {e}")

        return summary

    def get_depth_changes(
        self,
        stock: str,
        minutes: int = 5
    ) -> Dict[str, Any]:
        """
        Get changes in order book depth over time
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=minutes)

        # Get current and previous depth
        current = self.db.query(OrderBookDepth).filter(
            OrderBookDepth.stock == stock,
            OrderBookDepth.recorded_at >= cutoff
        ).order_by(
            OrderBookDepth.recorded_at.desc()
        ).first()

        previous = self.db.query(OrderBookDepth).filter(
            OrderBookDepth.stock == stock,
            OrderBookDepth.recorded_at < cutoff
        ).order_by(
            OrderBookDepth.recorded_at.desc()
        ).first()

        if not current or not previous:
            return {"error": "Insufficient data for comparison"}

        # Calculate changes
        changes = {
            "stock": stock,
            "time_period_minutes": minutes,
            "bid_qty_change": current.total_bid_qty - previous.total_bid_qty,
            "ask_qty_change": current.total_ask_qty - previous.total_ask_qty,
            "spread_change": current.spread - previous.spread,
            "bid_price_1_change": current.bid_price_1 - previous.bid_price_1,
            "ask_price_1_change": current.ask_price_1 - previous.ask_price_1,
            "current_timestamp": current.recorded_at.isoformat(),
            "previous_timestamp": previous.recorded_at.isoformat()
        }

        return changes
