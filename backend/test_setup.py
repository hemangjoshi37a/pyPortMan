"""
Test script for pyPortMan Backend
Run this to verify the setup is working correctly
"""

import sys
from datetime import datetime

print("=" * 50)
print("pyPortMan Backend Setup Test")
print("=" * 50)
print()

# Test 1: Check Python version
print(f"1. Python Version: {sys.version}")
print()

# Test 2: Check required packages
print("2. Checking required packages...")
required_packages = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "kiteconnect",
    "apscheduler",
    "python-dotenv",
    "httpx",
    "pandas",
    "pydantic"
]

missing_packages = []
for package in required_packages:
    try:
        __import__(package)
        print(f"   ✓ {package}")
    except ImportError:
        print(f"   ✗ {package} - NOT INSTALLED")
        missing_packages.append(package)

if missing_packages:
    print()
    print(f"   Missing packages: {', '.join(missing_packages)}")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)

print()

# Test 3: Check database setup
print("3. Testing database setup...")
try:
    from database import init_db, engine
    init_db()
    print("   ✓ Database initialized successfully")
except Exception as e:
    print(f"   ✗ Database error: {e}")
    sys.exit(1)

print()

# Test 4: Check models
print("4. Testing database models...")
try:
    from models import Account, Holding, Order, Position, PortfolioSnapshot
    print("   ✓ All models imported successfully")
except Exception as e:
    print(f"   ✗ Models error: {e}")
    sys.exit(1)

print()

# Test 5: Check scheduler
print("5. Testing scheduler...")
try:
    from scheduler import MarketScheduler
    scheduler = MarketScheduler()
    print(f"   ✓ Scheduler created")
    print(f"   - Market hours: {scheduler.market_start} - {scheduler.market_end}")
    print(f"   - Is market hours now: {scheduler.is_market_hours()}")
except Exception as e:
    print(f"   ✗ Scheduler error: {e}")
    sys.exit(1)

print()

# Test 6: Check KiteManager
print("6. Testing KiteManager...")
try:
    from kite_manager import KiteManager
    from database import SessionLocal
    db = SessionLocal()
    kite_manager = KiteManager(db)
    print("   ✓ KiteManager created successfully")
    db.close()
except Exception as e:
    print(f"   ✗ KiteManager error: {e}")
    sys.exit(1)

print()

# Test 7: Check FastAPI app
print("7. Testing FastAPI app...")
try:
    from main import app
    print("   ✓ FastAPI app created successfully")
    print(f"   - Title: {app.title}")
    print(f"   - Version: {app.version}")
except Exception as e:
    print(f"   ✗ FastAPI error: {e}")
    sys.exit(1)

print()
print("=" * 50)
print("All tests passed! ✓")
print("=" * 50)
print()
print("To start the server:")
print("  Windows: start_backend.bat")
print("  Linux/Mac: uvicorn main:app --reload")
print()
print("API Documentation: http://localhost:8000/docs")
print()
