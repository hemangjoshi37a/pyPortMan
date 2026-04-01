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
from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import Account, Holding, Order, Position, PortfolioSnapshot, GTTOrder
from kite_manager import KiteManager
from gtt_manager import GTTManager
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

# ==================== GTT MODELS ====================

class GTTOrderCreate(BaseModel):
    stock: str = Field(..., description="Trading symbol")
    exchange: str = Field(default="NSE", description="Exchange (NSE/BSE)")
    qty: int = Field(..., description="Quantity")
    buy_price: float = Field(..., description="Trigger price for buying")
    target_price: float = Field(..., description="Target price for selling")
    sl_price: float = Field(..., description="Stop loss price")
    allocation_pct: float = Field(default=0, description="% of account funds to allocate")

class GTTOrderUpdate(BaseModel):
    target_price: Optional[float] = None
    sl_price: Optional[float] = None
    qty: Optional[int] = None
    buy_price: Optional[float] = None
    allocation_pct: Optional[float] = None

class GTTOrderResponse(BaseModel):
    id: int
    account_id: int
    gtt_id: str
    stock: str
    exchange: str
    qty: int
    buy_price: float
    target_price: float
    sl_price: float
    allocation_pct: float
    status: str
    trigger_type: str
    triggered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class GTTBulkRequest(BaseModel):
    stock_list: List[GTTOrderCreate]

class GTTAllAccountsRequest(BaseModel):
    stock_list: List[GTTOrderCreate]

class GTTSummary(BaseModel):
    total_orders: int
    active_orders: int
    triggered_orders: int
    cancelled_orders: int
    expired_orders: int
    accounts_covered: int
    estimated_capital: float

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

# ==================== GTT ORDERS ====================

@app.get("/gtt", response_model=List[GTTOrderResponse])
def get_all_gtt_orders(db: Session = Depends(get_db)):
    """Get all GTT orders from all accounts"""
    return db.query(GTTOrder).order_by(GTTOrder.created_at.desc()).all()

@app.get("/gtt/{account_id}", response_model=List[GTTOrderResponse])
def get_gtt_orders(account_id: int, db: Session = Depends(get_db)):
    """Get GTT orders for a specific account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return db.query(GTTOrder).filter(GTTOrder.account_id == account_id).order_by(GTTOrder.created_at.desc()).all()

@app.get("/gtt/summary", response_model=GTTSummary)
def get_gtt_summary(db: Session = Depends(get_db)):
    """Get summary of all GTT orders"""
    gtt_manager = GTTManager(db, KiteManager(db))
    return gtt_manager.get_gtt_summary()

@app.post("/gtt")
def place_gtt_order(account_id: int, gtt: GTTOrderCreate, db: Session = Depends(get_db)):
    """Place a single GTT order"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    gtt_manager = GTTManager(db, KiteManager(db))
    try:
        result = gtt_manager.place_gtt(account_id, gtt.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/gtt/{gtt_id}")
def modify_gtt_order(gtt_id: str, gtt_update: GTTOrderUpdate, account_id: int, db: Session = Depends(get_db)):
    """Modify an existing GTT order"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    gtt_manager = GTTManager(db, KiteManager(db))
    try:
        result = gtt_manager.modify_gtt(account_id, gtt_id, gtt_update.model_dump(exclude_none=True))
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/gtt/{gtt_id}")
def delete_gtt_order(gtt_id: str, account_id: int, db: Session = Depends(get_db)):
    """Delete a GTT order"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    gtt_manager = GTTManager(db, KiteManager(db))
    try:
        gtt_manager.delete_gtt(account_id, gtt_id)
        return {"message": "GTT order deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gtt/bulk")
def place_bulk_gtt(account_id: int, request: GTTBulkRequest, db: Session = Depends(get_db)):
    """Place GTT orders for multiple stocks (one account)"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    gtt_manager = GTTManager(db, KiteManager(db))
    try:
        results = gtt_manager.place_bulk_gtt(account_id, [s.model_dump() for s in request.stock_list])
        return {"results": results}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gtt/bulk-all-accounts")
def place_gtt_all_accounts(request: GTTAllAccountsRequest, db: Session = Depends(get_db)):
    """Place same GTT orders across ALL accounts"""
    gtt_manager = GTTManager(db, KiteManager(db))
    try:
        results = gtt_manager.place_gtt_all_accounts([s.model_dump() for s in request.stock_list])
        return results
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gtt/sync")
def sync_gtt_status(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Sync GTT status from Zerodha to our database"""
    if account_id:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

    gtt_manager = GTTManager(db, KiteManager(db))
    try:
        result = gtt_manager.sync_gtt_status(account_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gtt/import-excel")
async def import_gtt_from_excel(
    account_id: Optional[int] = None,
    all_accounts: bool = False,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload stocks.xlsx and place GTT orders"""
    import openpyxl
    from io import BytesIO

    # Read Excel file
    contents = await file.read()
    workbook = openpyxl.load_workbook(BytesIO(contents))
    sheet = workbook.active

    # Parse Excel rows (skip header)
    stock_list = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row[0]:  # Skip empty rows
            continue

        # Expected columns: Symbol | Allocation% | Buy Price | Target Price | Stop Loss | Exchange | Qty
        stock_list.append({
            "stock": str(row[0]).strip(),
            "allocation_pct": float(row[1]) if row[1] else 0,
            "buy_price": float(row[2]) if row[2] else 0,
            "target_price": float(row[3]) if row[3] else 0,
            "sl_price": float(row[4]) if row[4] else 0,
            "exchange": str(row[5]).strip() if row[5] else "NSE",
            "qty": int(row[6]) if row[6] else 0
        })

    if not stock_list:
        raise HTTPException(status_code=400, detail="No valid data found in Excel file")

    gtt_manager = GTTManager(db, KiteManager(db))

    if all_accounts:
        # Place GTT for all accounts
        results = gtt_manager.place_gtt_all_accounts(stock_list)
        return {"message": f"Imported {len(stock_list)} stocks for all accounts", "results": results}
    elif account_id:
        # Place GTT for specific account
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        results = gtt_manager.place_bulk_gtt(account_id, stock_list)
        return {"message": f"Imported {len(stock_list)} stocks for account {account.name}", "results": results}
    else:
        # Return preview without placing
        return {"message": "Preview mode", "stock_list": stock_list, "count": len(stock_list)}

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
