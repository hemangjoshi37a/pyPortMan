"""
Watchlist Manager for pyPortMan
Manages watchlist operations including CRUD, price updates, and integration with other features
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import Watchlist, Account
from kite_manager import KiteManager

logger = logging.getLogger(__name__)


class WatchlistManager:
    """Manager for watchlist operations"""

    def __init__(self, db: Session):
        self.db = db
        self.kite_manager = KiteManager(db)

    def add_to_watchlist(self, account_id: int, stock_data: Dict[str, Any]) -> Watchlist:
        """
        Add a stock to watchlist

        Args:
            account_id: Account ID
            stock_data: Dictionary containing stock details
                - stock: Trading symbol (required)
                - exchange: Exchange (default: NSE)
                - category: Category/group name (default: Default)
                - notes: User notes
                - target_buy_price: Desired buy price
                - target_sell_price: Desired sell price
                - priority: Priority for sorting (default: 0)

        Returns:
            Watchlist object
        """
        # Check if stock already exists in watchlist
        existing = self.db.query(Watchlist).filter(
            and_(
                Watchlist.account_id == account_id,
                Watchlist.stock == stock_data.get("stock"),
                Watchlist.exchange == stock_data.get("exchange", "NSE"),
                Watchlist.is_active == True
            )
        ).first()

        if existing:
            raise ValueError(f"Stock {stock_data.get('stock')} already exists in watchlist")

        watchlist_item = Watchlist(
            account_id=account_id,
            stock=stock_data.get("stock"),
            exchange=stock_data.get("exchange", "NSE"),
            category=stock_data.get("category", "Default"),
            notes=stock_data.get("notes"),
            target_buy_price=stock_data.get("target_buy_price"),
            target_sell_price=stock_data.get("target_sell_price"),
            priority=stock_data.get("priority", 0)
        )

        self.db.add(watchlist_item)
        self.db.commit()
        self.db.refresh(watchlist_item)

        # Try to fetch current price
        self._update_stock_price(watchlist_item)

        logger.info(f"Added {watchlist_item.stock} to watchlist for account {account_id}")
        return watchlist_item

    def remove_from_watchlist(self, account_id: int, watchlist_id: int) -> bool:
        """
        Remove a stock from watchlist (soft delete)

        Args:
            account_id: Account ID
            watchlist_id: Watchlist item ID

        Returns:
            True if successful
        """
        item = self.db.query(Watchlist).filter(
            and_(
                Watchlist.id == watchlist_id,
                Watchlist.account_id == account_id
            )
        ).first()

        if not item:
            raise ValueError("Watchlist item not found")

        item.is_active = False
        item.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Removed {item.stock} from watchlist for account {account_id}")
        return True

    def get_watchlist(self, account_id: Optional[int] = None,
                     category: Optional[str] = None,
                     include_inactive: bool = False) -> List[Watchlist]:
        """
        Get watchlist items

        Args:
            account_id: Filter by account (None = all accounts)
            category: Filter by category (None = all categories)
            include_inactive: Include inactive items

        Returns:
            List of Watchlist objects
        """
        query = self.db.query(Watchlist)

        if account_id:
            query = query.filter(Watchlist.account_id == account_id)

        if category:
            query = query.filter(Watchlist.category == category)

        if not include_inactive:
            query = query.filter(Watchlist.is_active == True)

        # Sort by priority (descending) then by created_at (descending)
        items = query.order_by(Watchlist.priority.desc(), Watchlist.created_at.desc()).all()

        return items

    def get_categories(self, account_id: Optional[int] = None) -> List[str]:
        """
        Get all unique categories in watchlist

        Args:
            account_id: Filter by account (None = all accounts)

        Returns:
            List of category names
        """
        query = self.db.query(Watchlist.category).distinct()

        if account_id:
            query = query.filter(Watchlist.account_id == account_id)

        query = query.filter(Watchlist.is_active == True)

        categories = [row[0] for row in query.all()]
        return categories

    def update_watchlist_item(self, account_id: int, watchlist_id: int,
                              update_data: Dict[str, Any]) -> Watchlist:
        """
        Update a watchlist item

        Args:
            account_id: Account ID
            watchlist_id: Watchlist item ID
            update_data: Dictionary of fields to update

        Returns:
            Updated Watchlist object
        """
        item = self.db.query(Watchlist).filter(
            and_(
                Watchlist.id == watchlist_id,
                Watchlist.account_id == account_id
            )
        ).first()

        if not item:
            raise ValueError("Watchlist item not found")

        # Update allowed fields
        allowed_fields = {
            "category", "notes", "target_buy_price", "target_sell_price",
            "priority", "exchange"
        }

        for field, value in update_data.items():
            if field in allowed_fields:
                setattr(item, field, value)

        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Updated watchlist item {item.stock} for account {account_id}")
        return item

    def update_all_prices(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Update current prices for all active watchlist items

        Args:
            account_id: Filter by account (None = all accounts)

        Returns:
            Dictionary with update results
        """
        query = self.db.query(Watchlist).filter(Watchlist.is_active == True)

        if account_id:
            query = query.filter(Watchlist.account_id == account_id)

        items = query.all()

        updated_count = 0
        failed_count = 0
        results = []

        for item in items:
            try:
                self._update_stock_price(item)
                updated_count += 1
                results.append({
                    "stock": item.stock,
                    "status": "success",
                    "price": item.current_price
                })
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to update price for {item.stock}: {e}")
                results.append({
                    "stock": item.stock,
                    "status": "failed",
                    "error": str(e)
                })

        self.db.commit()

        return {
            "total": len(items),
            "updated": updated_count,
            "failed": failed_count,
            "results": results
        }

    def _update_stock_price(self, item: Watchlist) -> bool:
        """
        Update current price for a single watchlist item

        Args:
            item: Watchlist item

        Returns:
            True if successful
        """
        try:
            # Get quotes from Kite
            account = self.db.query(Account).filter(Account.id == item.account_id).first()
            if not account:
                return False

            kite = self.kite_manager.get_kite_instance(item.account_id)
            if not kite:
                return False

            # Get quote
            quote = kite.quote(f"{item.exchange}:{item.stock}")

            if quote and item.stock in quote:
                quote_data = quote[item.stock]
                old_price = item.current_price
                item.current_price = quote_data.get("last_price", 0)
                item.day_change = quote_data.get("change", 0)
                item.day_change_pct = quote_data.get("change_percentage", 0)
                item.last_price_update = datetime.utcnow()

                logger.debug(f"Updated price for {item.stock}: {old_price} -> {item.current_price}")
                return True

        except Exception as e:
            logger.error(f"Error updating price for {item.stock}: {e}")

        return False

    def get_watchlist_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary statistics for watchlist

        Args:
            account_id: Filter by account (None = all accounts)

        Returns:
            Dictionary with summary stats
        """
        query = self.db.query(Watchlist).filter(Watchlist.is_active == True)

        if account_id:
            query = query.filter(Watchlist.account_id == account_id)

        items = query.all()

        total_items = len(items)
        total_value = sum(item.current_price for item in items if item.current_price > 0)
        avg_change_pct = sum(item.day_change_pct for item in items) / total_items if total_items > 0 else 0

        gainers = [item for item in items if item.day_change_pct > 0]
        losers = [item for item in items if item.day_change_pct < 0]

        # Get category breakdown
        category_counts = {}
        for item in items:
            category = item.category or "Default"
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_items": total_items,
            "total_value": total_value,
            "avg_change_pct": round(avg_change_pct, 2),
            "gainers_count": len(gainers),
            "losers_count": len(losers),
            "categories": category_counts,
            "top_gainer": max(gainers, key=lambda x: x.day_change_pct) if gainers else None,
            "top_loser": min(losers, key=lambda x: x.day_change_pct) if losers else None
        }

    def search_watchlist(self, account_id: int, search_term: str) -> List[Watchlist]:
        """
        Search watchlist by stock symbol or notes

        Args:
            account_id: Account ID
            search_term: Search term

        Returns:
            List of matching Watchlist objects
        """
        search_pattern = f"%{search_term}%"

        items = self.db.query(Watchlist).filter(
            and_(
                Watchlist.account_id == account_id,
                Watchlist.is_active == True,
                or_(
                    Watchlist.stock.ilike(search_pattern),
                    Watchlist.notes.ilike(search_pattern)
                )
            )
        ).order_by(Watchlist.priority.desc()).all()

        return items

    def bulk_add_to_watchlist(self, account_id: int, stock_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add multiple stocks to watchlist

        Args:
            account_id: Account ID
            stock_list: List of stock data dictionaries

        Returns:
            Dictionary with results
        """
        results = {
            "total": len(stock_list),
            "added": 0,
            "skipped": 0,
            "failed": 0,
            "items": []
        }

        for stock_data in stock_list:
            try:
                item = self.add_to_watchlist(account_id, stock_data)
                results["added"] += 1
                results["items"].append({
                    "stock": item.stock,
                    "status": "added"
                })
            except ValueError as e:
                if "already exists" in str(e):
                    results["skipped"] += 1
                    results["items"].append({
                        "stock": stock_data.get("stock"),
                        "status": "skipped",
                        "reason": str(e)
                    })
                else:
                    results["failed"] += 1
                    results["items"].append({
                        "stock": stock_data.get("stock"),
                        "status": "failed",
                        "reason": str(e)
                    })
            except Exception as e:
                results["failed"] += 1
                results["items"].append({
                    "stock": stock_data.get("stock"),
                    "status": "failed",
                    "reason": str(e)
                })

        return results

    def get_price_targets(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Get stocks that are near their target buy/sell prices

        Args:
            account_id: Account ID

        Returns:
            List of stocks near targets
        """
        items = self.db.query(Watchlist).filter(
            and_(
                Watchlist.account_id == account_id,
                Watchlist.is_active == True,
                Watchlist.current_price > 0
            )
        ).all()

        near_targets = []

        for item in items:
            if item.target_buy_price:
                buy_diff_pct = ((item.current_price - item.target_buy_price) / item.target_buy_price) * 100
                if abs(buy_diff_pct) <= 5:  # Within 5% of target
                    near_targets.append({
                        "stock": item.stock,
                        "current_price": item.current_price,
                        "target_type": "BUY",
                        "target_price": item.target_buy_price,
                        "diff_pct": round(buy_diff_pct, 2)
                    })

            if item.target_sell_price:
                sell_diff_pct = ((item.current_price - item.target_sell_price) / item.target_sell_price) * 100
                if abs(sell_diff_pct) <= 5:  # Within 5% of target
                    near_targets.append({
                        "stock": item.stock,
                        "current_price": item.current_price,
                        "target_type": "SELL",
                        "target_price": item.target_sell_price,
                        "diff_pct": round(sell_diff_pct, 2)
                    })

        return near_targets
