"""
Test script for Watchlist Management feature
Run this to verify the watchlist functionality
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import init_db, get_db
from watchlist_manager import WatchlistManager
from models import Watchlist, Account


def test_watchlist():
    """Test watchlist functionality"""
    print("=" * 50)
    print("Testing Watchlist Management Feature")
    print("=" * 50)

    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("   ✓ Database initialized")

    # Get database session
    db = next(get_db())
    manager = WatchlistManager(db)

    # Test 1: Get categories (should be empty initially)
    print("\n2. Getting categories...")
    categories = manager.get_categories()
    print(f"   Categories: {categories}")

    # Test 2: Get watchlist summary
    print("\n3. Getting watchlist summary...")
    summary = manager.get_watchlist_summary()
    print(f"   Total items: {summary['total_items']}")
    print(f"   Total value: {summary['total_value']}")

    # Test 3: Add stock to watchlist (requires an account)
    print("\n4. Checking for existing accounts...")
    accounts = db.query(Account).filter(Account.is_active == True).all()
    if accounts:
        account = accounts[0]
        print(f"   Found account: {account.name} (ID: {account.id})")

        # Test adding a stock
        print(f"\n5. Adding RELIANCE to watchlist...")
        try:
            item = manager.add_to_watchlist(account.id, {
                "stock": "RELIANCE",
                "exchange": "NSE",
                "category": "Large Cap",
                "notes": "Reliance Industries - Good for long term",
                "target_buy_price": 2400.0,
                "target_sell_price": 2800.0,
                "priority": 5
            })
            print(f"   ✓ Added: {item.stock} (ID: {item.id})")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Test getting watchlist
        print(f"\n6. Getting watchlist for account...")
        watchlist = manager.get_watchlist(account.id)
        print(f"   Items in watchlist: {len(watchlist)}")
        for item in watchlist:
            print(f"   - {item.stock} ({item.category}): ₹{item.current_price}")

        # Test getting summary again
        print(f"\n7. Getting updated watchlist summary...")
        summary = manager.get_watchlist_summary(account.id)
        print(f"   Total items: {summary['total_items']}")
        print(f"   Categories: {summary['categories']}")

        # Test search
        print(f"\n8. Searching watchlist...")
        results = manager.search_watchlist(account.id, "RELIANCE")
        print(f"   Found {len(results)} results")

        # Test bulk add
        print(f"\n9. Testing bulk add...")
        try:
            bulk_result = manager.bulk_add_to_watchlist(account.id, [
                {"stock": "TCS", "exchange": "NSE", "category": "IT"},
                {"stock": "INFY", "exchange": "NSE", "category": "IT"},
            ])
            print(f"   Added: {bulk_result['added']}, Skipped: {bulk_result['skipped']}, Failed: {bulk_result['failed']}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Test update
        print(f"\n10. Testing update...")
        if watchlist:
            try:
                updated = manager.update_watchlist_item(account.id, watchlist[0].id, {
                    "notes": "Updated notes for testing",
                    "priority": 10
                })
                print(f"   ✓ Updated: {updated.stock}")
            except Exception as e:
                print(f"   ✗ Error: {e}")

        # Test remove
        print(f"\n11. Testing remove...")
        if watchlist:
            try:
                manager.remove_from_watchlist(account.id, watchlist[0].id)
                print(f"   ✓ Removed: {watchlist[0].stock}")
            except Exception as e:
                print(f"   ✗ Error: {e}")

    else:
        print("   ⚠ No active accounts found. Create an account first to test watchlist.")

    db.close()
    print("\n" + "=" * 50)
    print("Test completed!")
    print("=" * 50)


if __name__ == "__main__":
    test_watchlist()
