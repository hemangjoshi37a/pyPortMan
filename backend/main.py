"""
FastAPI Backend for pyPortMan
REST API for Zerodha KiteConnect multi-account portfolio management

First-time setup instructions:
1. Install dependencies: pip install -r requirements.txt
2. Copy .env.example to .env and configure your settings
3. Start the server: uvicorn main:app --reload
4. Add your first Zerodha account via POST /accounts
5. Get login URL via GET /accounts/{id}/token-url
6. Complete Zerodha login and get request_token
7. Call POST /auth/callback with request_token to generate access token
8. Your account is now ready to use!

Note: KiteConnect access tokens expire daily at 6 AM IST.
You'll need to re-login each day to get a new token.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import Account, Holding, Order, Position, PortfolioSnapshot
from kite_manager import KiteManager
from scheduler import get_scheduler

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="pyPortMan API",
    description="Zerodha KiteConnect Multi-Account Portfolio Management API",
    version="1.0.0"
)

# CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class AccountCreate(BaseModel):
    name: str = Field(..., description="Account name/alias")
    account_id: str = Field(..., description="Zerodha user ID")
    api_key: str = Field(..., description="Zerodha API key")
    api_secret: str = Field(..., description="Zerodha API secret")

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    is_active: Optional[bool] = None

class AccountResponse(BaseModel):
    id: int
    name: str
    account_id: str
    is_active: bool
    added_at: datetime
    last_login_at: Optional[datetime]
    token_expires_at: Optional[datetime]

    class Config:
        from_attributes = True

class HoldingResponse(BaseModel):
    id: int
    account_id: int
    stock: str
    exchange: str
    qty: int
    avg_price: float
    ltp: float
    current_value: float
    pnl: float
    pnl_percent: float
    product: str
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    account_id: int
    order_id: str
    stock: str
    exchange: str
    qty: int
    price: float
    order_type: str
    transaction_type: str
    status: str
    product: str
    placed_at: datetime

    class Config:
        from_attributes = True

class PositionResponse(BaseModel):
    id: int
    account_id: int
    stock: str
    exchange: str
    qty: int
    avg_price: float
    ltp: float
    pnl: float
    pnl_percent: float
    product: str
    product_type: str
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderPlaceRequest(BaseModel):
    tradingsymbol: str
    exchange: str = "NSE"
    transaction_type: str  # BUY or SELL
    quantity: int
    order_type: str = "MARKET"  # MARKET, LIMIT, SL, SL-M
    product: str = "CNC"  # CNC, MIS, CO, BO
    price: Optional[float] = None  # Required for LIMIT orders
    validity: str = "DAY"
    variety: str = "regular"

class PositionSquareoffRequest(BaseModel):
    tradingsymbol: str
    exchange: str = "NSE"
    order_type: str = "MARKET"
    product: str = "MIS"

class AuthCallbackRequest(BaseModel):
    account_id: int
    request_token: str

class PortfolioSummary(BaseModel):
    total_value: float
    investment_value: float
    day_pnl: float
    day_pnl_percent: float
    holdings_count: int
    positions_count: int
    accounts_count: int

class AllocationItem(BaseModel):
    stock: str
    value: float
    percentage: float

class StockPnL(BaseModel):
    stock: str
    pnl: float
    pnl_percent: float
    current_value: float

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and start scheduler on startup"""
    init_db()
    scheduler = get_scheduler()
    scheduler.start()
    print("pyPortMan API started successfully!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown"""
    scheduler = get_scheduler()
    scheduler.stop()
    print("pyPortMan API stopped!")

# ==================== ACCOUNTS ====================

@app.get("/accounts", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    """Get all accounts"""
    return db.query(Account).filter(Account.is_active == True).all()

@app.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    """Add a new Zerodha account"""
    # Check if account_id already exists
    existing = db.query(Account).filter(Account.account_id == account.account_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account ID already exists")

    new_account = Account(
        name=account.name,
        account_id=account.account_id,
        api_key=account.api_key,
        api_secret=account.api_secret,
        is_active=True
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    # Add scheduler jobs for this account
    scheduler = get_scheduler()
    scheduler.add_account_job(new_account.id)

    return new_account

@app.put("/accounts/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, account_update: AccountUpdate, db: Session = Depends(get_db)):
    """Update an account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    for field, value in account_update.model_dump(exclude_unset=True).items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account

@app.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """Remove an account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Remove scheduler jobs
    scheduler = get_scheduler()
    scheduler.remove_account_job(account_id)

    # Soft delete
    account.is_active = False
    db.commit()

@app.get("/accounts/{id}/token-url")
def get_token_url(id: int, db: Session = Depends(get_db)):
    """Get Zerodha login URL for obtaining request token"""
    account = db.query(Account).filter(Account.id == id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    login_url = kite_manager.generate_login_url(id)

    if not login_url:
        raise HTTPException(status_code=500, detail="Failed to generate login URL")

    return {"login_url": login_url}

# ==================== HOLDINGS ====================

@app.get("/holdings", response_model=List[HoldingResponse])
def get_all_holdings(db: Session = Depends(get_db)):
    """Get all holdings from all accounts"""
    return db.query(Holding).all()

@app.get("/holdings/{account_id}", response_model=List[HoldingResponse])
def get_holdings(account_id: int, db: Session = Depends(get_db)):
    """Get holdings for a specific account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return db.query(Holding).filter(Holding.account_id == account_id).all()

@app.post("/holdings/refresh")
def refresh_holdings(account_id: int, db: Session = Depends(get_db)):
    """Fetch fresh holdings from Zerodha API"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    try:
        holdings = kite_manager.fetch_holdings(account_id)
        return {"message": f"Refreshed {len(holdings)} holdings"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== POSITIONS ====================

@app.get("/positions", response_model=List[PositionResponse])
def get_all_positions(db: Session = Depends(get_db)):
    """Get all open positions from all accounts"""
    return db.query(Position).all()

@app.get("/positions/{account_id}", response_model=List[PositionResponse])
def get_positions(account_id: int, db: Session = Depends(get_db)):
    """Get positions for a specific account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return db.query(Position).filter(Position.account_id == account_id).all()

@app.post("/positions/{account_id}/squareoff-all")
def squareoff_all_positions(account_id: int, db: Session = Depends(get_db)):
    """Square off all positions for an account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    try:
        results = kite_manager.squareoff_all_positions(account_id)
        return {"results": results}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/positions/squareoff")
def squareoff_position(account_id: int, params: PositionSquareoffRequest, db: Session = Depends(get_db)):
    """Square off a single position"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    try:
        result = kite_manager.squareoff_position(account_id, params.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ORDERS ====================

@app.get("/orders", response_model=List[OrderResponse])
def get_all_orders(db: Session = Depends(get_db)):
    """Get all orders from all accounts"""
    return db.query(Order).order_by(Order.placed_at.desc()).all()

@app.get("/orders/{account_id}", response_model=List[OrderResponse])
def get_orders(account_id: int, db: Session = Depends(get_db)):
    """Get orders for a specific account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return db.query(Order).filter(Order.account_id == account_id).order_by(Order.placed_at.desc()).all()

@app.post("/orders")
def place_order(account_id: int, order: OrderPlaceRequest, db: Session = Depends(get_db)):
    """Place a new order"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    try:
        result = kite_manager.place_order(account_id, order.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/orders/{order_id}")
def cancel_order(order_id: str, account_id: int, db: Session = Depends(get_db)):
    """Cancel an order"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    try:
        kite_manager.cancel_order(account_id, order_id)
        return {"message": "Order cancelled successfully"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== STATS ====================

@app.get("/stats/summary", response_model=PortfolioSummary)
def get_portfolio_summary(db: Session = Depends(get_db)):
    """Get combined portfolio stats across all accounts"""
    accounts = db.query(Account).filter(Account.is_active == True).all()

    total_value = 0
    investment_value = 0
    day_pnl = 0
    holdings_count = 0
    positions_count = 0

    for account in accounts:
        holdings = db.query(Holding).filter(Holding.account_id == account.id).all()
        positions = db.query(Position).filter(Position.account_id == account.id).all()

        total_value += sum(h.current_value for h in holdings)
        investment_value += sum(h.qty * h.avg_price for h in holdings)
        day_pnl += sum(h.pnl for h in holdings) + sum(p.pnl for p in positions)
        holdings_count += len(holdings)
        positions_count += len(positions)

    day_pnl_percent = (day_pnl / investment_value * 100) if investment_value > 0 else 0

    return PortfolioSummary(
        total_value=total_value,
        investment_value=investment_value,
        day_pnl=day_pnl,
        day_pnl_percent=day_pnl_percent,
        holdings_count=holdings_count,
        positions_count=positions_count,
        accounts_count=len(accounts)
    )

@app.get("/stats/equity")
def get_equity_curve(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Get 30-day portfolio value history"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    snapshots = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.recorded_at >= cutoff_date
    ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

    return [
        {
            "date": s.recorded_at.isoformat(),
            "total_value": s.total_value,
            "day_pnl": s.day_pnl,
            "day_pnl_percent": s.day_pnl_percent
        }
        for s in snapshots
    ]

@app.get("/stats/allocation")
def get_allocation(db: Session = Depends(get_db)):
    """Get sector/stock allocation breakdown"""
    holdings = db.query(Holding).all()

    total_value = sum(h.current_value for h in holdings)

    allocation = {}
    for h in holdings:
        if h.stock not in allocation:
            allocation[h.stock] = 0
        allocation[h.stock] += h.current_value

    result = [
        AllocationItem(
            stock=stock,
            value=value,
            percentage=(value / total_value * 100) if total_value > 0 else 0
        )
        for stock, value in allocation.items()
    ]

    # Sort by percentage descending
    result.sort(key=lambda x: x.percentage, reverse=True)

    return result

@app.get("/stats/top-gainers", response_model=List[StockPnL])
def get_top_gainers(limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """Get top 5 gaining stocks today"""
    holdings = db.query(Holding).all()

    result = [
        StockPnL(
            stock=h.stock,
            pnl=h.pnl,
            pnl_percent=h.pnl_percent,
            current_value=h.current_value
        )
        for h in holdings
    ]

    # Sort by pnl descending
    result.sort(key=lambda x: x.pnl, reverse=True)

    return result[:limit]

@app.get("/stats/top-losers", response_model=List[StockPnL])
def get_top_losers(limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """Get top 5 losing stocks today"""
    holdings = db.query(Holding).all()

    result = [
        StockPnL(
            stock=h.stock,
            pnl=h.pnl,
            pnl_percent=h.pnl_percent,
            current_value=h.current_value
        )
        for h in holdings
    ]

    # Sort by pnl ascending
    result.sort(key=lambda x: x.pnl)

    return result[:limit]

# ==================== AUTH ====================

@app.get("/auth/login-url/{account_id}")
def get_login_url(account_id: int, db: Session = Depends(get_db)):
    """Generate Zerodha login URL for authentication"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    login_url = kite_manager.generate_login_url(account_id)

    if not login_url:
        raise HTTPException(status_code=500, detail="Failed to generate login URL")

    return {"login_url": login_url}

@app.post("/auth/callback")
def handle_auth_callback(callback: AuthCallbackRequest, db: Session = Depends(get_db)):
    """Handle access token after Zerodha login"""
    account = db.query(Account).filter(Account.id == callback.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    kite_manager = KiteManager(db)
    success = kite_manager.generate_session(callback.account_id, callback.request_token)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to generate access token")

    return {"message": "Access token generated successfully"}

# ==================== HEALTH ====================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler_running": get_scheduler().is_running
    }

# ==================== ROOT ====================

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "pyPortMan API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
