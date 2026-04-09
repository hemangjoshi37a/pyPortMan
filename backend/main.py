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
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

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

from database import get_db, init_db
from models import Account, Holding, Order, Position, PortfolioSnapshot, GTTOrder, AlertConfig, AlertHistory, PriceAlert, Watchlist
from kite_manager import KiteManager
from gtt_manager import GTTManager
from scheduler import get_scheduler
from telegram_alerts import TelegramAlerts
from auto_login import AutoLoginManager, run_async
from price_alerts import PriceAlertManager
from analytics import AnalyticsManager
from watchlist_manager import WatchlistManager

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

# ==================== ALERT MODELS ====================

class AlertConfigCreate(BaseModel):
    bot_token: str = Field(..., description="Telegram bot token")
    chat_id: str = Field(..., description="Telegram chat ID")

class AlertConfigUpdate(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    gtt_alerts_enabled: Optional[bool] = None
    loss_alerts_enabled: Optional[bool] = None
    daily_summary_enabled: Optional[bool] = None
    order_alerts_enabled: Optional[bool] = None
    loss_threshold_pct: Optional[float] = None

class AlertConfigResponse(BaseModel):
    id: int
    chat_id: Optional[str]
    bot_token_masked: Optional[str]
    gtt_alerts_enabled: bool
    loss_alerts_enabled: bool
    daily_summary_enabled: bool
    order_alerts_enabled: bool
    loss_threshold_pct: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AlertHistoryResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    sent_at: datetime
    success: bool

    class Config:
        from_attributes = True

# ==================== AUTO LOGIN MODELS ====================

class AutoLoginCredentials(BaseModel):
    password: str = Field(..., description="Zerodha password")
    totp_secret: str = Field(..., description="TOTP secret from Google Authenticator")

class AutoLoginStatusResponse(BaseModel):
    account_id: int
    account_name: str
    auto_login_enabled: bool
    has_credentials: bool
    last_token_refresh: Optional[datetime]
    token_expires_at: Optional[datetime]
    token_expired: bool

class TokenRefreshResult(BaseModel):
    account_id: int
    account_name: str
    status: str
    error: Optional[str] = None
    token_expires_at: Optional[str] = None

class TokenRefreshSummary(BaseModel):
    total: int
    success: int
    failed: int
    accounts: List[TokenRefreshResult]

# ==================== PRICE ALERT MODELS ====================

class PriceAlertCreate(BaseModel):
    stock: str = Field(..., description="Trading symbol")
    exchange: str = Field(default="NSE", description="Exchange (NSE/BSE)")
    alert_type: str = Field(..., description="Alert type: ABOVE or BELOW")
    target_price: float = Field(..., description="Target price")
    repeat: bool = Field(default=False, description="Whether to repeat alert")
    repeat_interval: int = Field(default=24, description="Repeat interval in hours")

class PriceAlertUpdate(BaseModel):
    target_price: Optional[float] = None
    alert_type: Optional[str] = None
    repeat: Optional[bool] = None
    repeat_interval: Optional[int] = None
    status: Optional[str] = None

class PriceAlertResponse(BaseModel):
    id: int
    account_id: int
    stock: str
    exchange: str
    alert_type: str
    target_price: float
    current_price: float
    status: str
    repeat: bool
    repeat_interval: int
    triggered_count: int
    triggered_at: Optional[datetime]
    next_trigger_at: Optional[datetime]
    last_checked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PriceAlertSummary(BaseModel):
    total: int
    active: int
    triggered: int
    completed: int

# ==================== WATCHLIST MODELS ====================

class WatchlistCreate(BaseModel):
    stock: str = Field(..., description="Trading symbol")
    exchange: str = Field(default="NSE", description="Exchange (NSE/BSE)")
    category: str = Field(default="Default", description="Category/group name")
    notes: Optional[str] = Field(None, description="User notes about the stock")
    target_buy_price: Optional[float] = Field(None, description="Desired buy price")
    target_sell_price: Optional[float] = Field(None, description="Desired sell price")
    priority: int = Field(default=0, description="Priority for sorting (higher = first)")

class WatchlistUpdate(BaseModel):
    category: Optional[str] = None
    notes: Optional[str] = None
    target_buy_price: Optional[float] = None
    target_sell_price: Optional[float] = None
    priority: Optional[int] = None
    exchange: Optional[str] = None

class WatchlistResponse(BaseModel):
    id: int
    account_id: int
    stock: str
    exchange: str
    category: str
    notes: Optional[str]
    target_buy_price: Optional[float]
    target_sell_price: Optional[float]
    current_price: float
    day_change: float
    day_change_pct: float
    is_active: bool
    priority: int
    last_price_update: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WatchlistBulkRequest(BaseModel):
    stock_list: List[WatchlistCreate]

class WatchlistSummary(BaseModel):
    total_items: int
    total_value: float
    avg_change_pct: float
    gainers_count: int
    losers_count: int
    categories: Dict[str, int]
    top_gainer: Optional[Dict[str, Any]]
    top_loser: Optional[Dict[str, Any]]

class PriceTargetItem(BaseModel):
    stock: str
    current_price: float
    target_type: str
    target_price: float
    diff_pct: float

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

        # Send Telegram alert for order placed
        try:
            telegram = TelegramAlerts(db)
            telegram.send_order_placed_alert(
                account_id=account_id,
                account_name=account.name,
                stock=order.tradingsymbol,
                qty=order.quantity,
                price=order.price or 0,
                order_type=order.order_type,
                transaction_type=order.transaction_type
            )
        except Exception as e:
            logger.error(f"Error sending order alert: {e}")

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

        # Send Telegram alert for order cancelled
        try:
            telegram = TelegramAlerts(db)
            # Get order details
            order_record = db.query(Order).filter(Order.order_id == order_id).first()
            if order_record:
                telegram.send_order_cancelled_alert(
                    account_id=account_id,
                    account_name=account.name,
                    stock=order_record.stock,
                    order_id=order_id
                )
        except Exception as e:
            logger.error(f"Error sending order cancel alert: {e}")

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

# ==================== ALERTS ====================

@app.get("/alerts/config", response_model=AlertConfigResponse)
def get_alert_config(db: Session = Depends(get_db)):
    """Get Telegram alert configuration"""
    config = db.query(AlertConfig).first()
    if not config:
        # Return default config
        return AlertConfigResponse(
            id=0,
            chat_id=None,
            bot_token_masked=None,
            gtt_alerts_enabled=True,
            loss_alerts_enabled=True,
            daily_summary_enabled=True,
            order_alerts_enabled=True,
            loss_threshold_pct=5.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    # Mask bot token for security
    masked_token = None
    if config.bot_token:
        masked_token = config.bot_token[:8] + "..." + config.bot_token[-4:] if len(config.bot_token) > 12 else "***"

    return AlertConfigResponse(
        id=config.id,
        chat_id=config.chat_id,
        bot_token_masked=masked_token,
        gtt_alerts_enabled=config.gtt_alerts_enabled,
        loss_alerts_enabled=config.loss_alerts_enabled,
        daily_summary_enabled=config.daily_summary_enabled,
        order_alerts_enabled=config.order_alerts_enabled,
        loss_threshold_pct=config.loss_threshold_pct,
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@app.post("/alerts/config", response_model=AlertConfigResponse)
def save_alert_config(config_data: AlertConfigCreate, db: Session = Depends(get_db)):
    """Save Telegram alert configuration"""
    config = db.query(AlertConfig).first()

    if config:
        # Update existing config
        config.bot_token = config_data.bot_token
        config.chat_id = config_data.chat_id
        config.updated_at = datetime.utcnow()
    else:
        # Create new config
        config = AlertConfig(
            bot_token=config_data.bot_token,
            chat_id=config_data.chat_id,
            gtt_alerts_enabled=True,
            loss_alerts_enabled=True,
            daily_summary_enabled=True,
            order_alerts_enabled=True,
            loss_threshold_pct=5.0
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    # Mask bot token for response
    masked_token = config.bot_token[:8] + "..." + config.bot_token[-4:] if len(config.bot_token) > 12 else "***"

    return AlertConfigResponse(
        id=config.id,
        chat_id=config.chat_id,
        bot_token_masked=masked_token,
        gtt_alerts_enabled=config.gtt_alerts_enabled,
        loss_alerts_enabled=config.loss_alerts_enabled,
        daily_summary_enabled=config.daily_summary_enabled,
        order_alerts_enabled=config.order_alerts_enabled,
        loss_threshold_pct=config.loss_threshold_pct,
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@app.put("/alerts/config", response_model=AlertConfigResponse)
def update_alert_config(config_update: AlertConfigUpdate, db: Session = Depends(get_db)):
    """Update Telegram alert configuration settings"""
    config = db.query(AlertConfig).first()
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found. Please create config first.")

    for field, value in config_update.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)

    # Mask bot token for response
    masked_token = config.bot_token[:8] + "..." + config.bot_token[-4:] if len(config.bot_token) > 12 else "***"

    return AlertConfigResponse(
        id=config.id,
        chat_id=config.chat_id,
        bot_token_masked=masked_token,
        gtt_alerts_enabled=config.gtt_alerts_enabled,
        loss_alerts_enabled=config.loss_alerts_enabled,
        daily_summary_enabled=config.daily_summary_enabled,
        order_alerts_enabled=config.order_alerts_enabled,
        loss_threshold_pct=config.loss_threshold_pct,
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@app.post("/alerts/test")
def test_alert(db: Session = Depends(get_db)):
    """Send a test message to Telegram"""
    telegram = TelegramAlerts(db)
    result = telegram.test_connection()
    return result

@app.get("/alerts/history", response_model=List[AlertHistoryResponse])
def get_alert_history(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """Get recent alert history"""
    telegram = TelegramAlerts(db)
    return telegram.get_alert_history(limit)

@app.post("/alerts/toggle/{alert_type}")
def toggle_alert(alert_type: str, enabled: bool = Query(...), db: Session = Depends(get_db)):
    """Enable/disable specific alert type"""
    config = db.query(AlertConfig).first()
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")

    valid_types = ["gtt", "loss", "daily_summary", "order"]
    if alert_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid alert type. Must be one of: {', '.join(valid_types)}")

    # Map alert type to config field
    field_map = {
        "gtt": "gtt_alerts_enabled",
        "loss": "loss_alerts_enabled",
        "daily_summary": "daily_summary_enabled",
        "order": "order_alerts_enabled"
    }

    setattr(config, field_map[alert_type], enabled)
    config.updated_at = datetime.utcnow()
    db.commit()

    return {"message": f"{alert_type}_alerts_enabled set to {enabled}"}

# ==================== AUTO LOGIN ====================

@app.get("/auto-login/status/{account_id}", response_model=AutoLoginStatusResponse)
def get_auto_login_status(account_id: int, db: Session = Depends(get_db)):
    """Get auto-login status for an account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = AutoLoginManager(db)
    return manager.get_auto_login_status(account_id)

@app.post("/auto-login/credentials/{account_id}")
def save_auto_login_credentials(account_id: int, credentials: AutoLoginCredentials, db: Session = Depends(get_db)):
    """Save encrypted credentials for auto-login"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = AutoLoginManager(db)
    success = manager.save_credentials(account_id, credentials.password, credentials.totp_secret)

    if success:
        return {"message": "Credentials saved successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save credentials")

@app.delete("/auto-login/credentials/{account_id}")
def remove_auto_login_credentials(account_id: int, db: Session = Depends(get_db)):
    """Remove credentials and disable auto-login"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = AutoLoginManager(db)
    success = manager.remove_credentials(account_id)

    if success:
        return {"message": "Credentials removed successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to remove credentials")

@app.post("/auto-login/refresh/{account_id}")
def refresh_account_token(account_id: int, db: Session = Depends(get_db)):
    """Manually refresh access token for a specific account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = AutoLoginManager(db)
    access_token = run_async(manager.refresh_account(account_id))

    if access_token:
        return {"message": "Token refreshed successfully", "token_expires_at": account.token_expires_at.isoformat()}
    else:
        raise HTTPException(status_code=500, detail="Failed to refresh token")

@app.post("/auto-login/refresh-all")
def refresh_all_tokens(db: Session = Depends(get_db)):
    """Refresh tokens for all accounts with auto-login enabled"""
    manager = AutoLoginManager(db)
    results = run_async(manager.refresh_all_accounts())
    return results

@app.put("/auto-login/toggle/{account_id}")
def toggle_auto_login(account_id: int, enabled: bool = Query(...), db: Session = Depends(get_db)):
    """Enable/disable auto-login for an account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if enabled and not (account.password and account.totp_secret):
        raise HTTPException(status_code=400, detail="Credentials must be saved before enabling auto-login")

    account.auto_login_enabled = enabled
    db.commit()

    return {"message": f"Auto-login {'enabled' if enabled else 'disabled'} for account {account.name}"}

# ==================== PRICE ALERTS ====================

@app.get("/price-alerts", response_model=List[PriceAlertResponse])
def get_price_alerts(account_id: Optional[int] = None, status: str = "ACTIVE", db: Session = Depends(get_db)):
    """Get price alerts"""
    manager = PriceAlertManager(db)
    return manager.get_alerts(account_id, status)

@app.get("/price-alerts/{alert_id}", response_model=PriceAlertResponse)
def get_price_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a specific price alert"""
    manager = PriceAlertManager(db)
    alert = manager.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@app.post("/price-alerts", response_model=PriceAlertResponse, status_code=status.HTTP_201_CREATED)
def create_price_alert(account_id: int, alert: PriceAlertCreate, db: Session = Depends(get_db)):
    """Create a new price alert"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if alert.alert_type not in ["ABOVE", "BELOW"]:
        raise HTTPException(status_code=400, detail="alert_type must be 'ABOVE' or 'BELOW'")

    manager = PriceAlertManager(db)
    alert_data = alert.model_dump()
    alert_data["account_id"] = account_id

    created_alert = manager.create_alert(alert_data)
    return created_alert

@app.put("/price-alerts/{alert_id}", response_model=PriceAlertResponse)
def update_price_alert(alert_id: int, alert_update: PriceAlertUpdate, db: Session = Depends(get_db)):
    """Update a price alert"""
    manager = PriceAlertManager(db)
    updated_alert = manager.update_alert(alert_id, alert_update.model_dump(exclude_none=True))

    if not updated_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return updated_alert

@app.delete("/price-alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete a price alert"""
    manager = PriceAlertManager(db)
    success = manager.delete_alert(alert_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

@app.get("/price-alerts/summary", response_model=PriceAlertSummary)
def get_price_alert_summary(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get summary of price alerts"""
    manager = PriceAlertManager(db)
    return manager.get_alert_summary(account_id)

@app.post("/price-alerts/check")
def check_price_alerts(db: Session = Depends(get_db)):
    """Manually check all active price alerts"""
    manager = PriceAlertManager(db)
    triggered = manager.check_alerts()
    return {"triggered_count": len(triggered), "alerts": triggered}

@app.post("/price-alerts/cleanup")
def cleanup_old_price_alerts(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Clean up old completed alerts"""
    manager = PriceAlertManager(db)
    deleted = manager.cleanup_old_alerts(days)
    return {"deleted_count": deleted}

# ==================== ANALYTICS ====================

@app.get("/analytics/overview")
def get_analytics_overview(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get comprehensive portfolio overview"""
    manager = AnalyticsManager(db)
    return manager.get_portfolio_overview(account_id)

@app.get("/analytics/allocation")
def get_analytics_allocation(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get stock-wise allocation breakdown"""
    manager = AnalyticsManager(db)
    return manager.get_stock_allocation(account_id)

@app.get("/analytics/pnl-breakdown")
def get_analytics_pnl_breakdown(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get detailed P&L breakdown"""
    manager = AnalyticsManager(db)
    return manager.get_pnl_breakdown(account_id)

@app.get("/analytics/risk-metrics")
def get_analytics_risk_metrics(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Calculate risk metrics for the portfolio"""
    manager = AnalyticsManager(db)
    return manager.get_risk_metrics(account_id)

@app.get("/analytics/equity-curve")
def get_analytics_equity_curve(days: int = Query(30, ge=1, le=365), account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get equity curve data for charting"""
    manager = AnalyticsManager(db)
    return manager.get_equity_curve(days, account_id)

@app.get("/analytics/account-comparison")
def get_analytics_account_comparison(db: Session = Depends(get_db)):
    """Get comparison data across all accounts"""
    manager = AnalyticsManager(db)
    return manager.get_account_comparison()

@app.get("/analytics/performance-summary")
def get_analytics_performance_summary(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Get performance summary over a period"""
    manager = AnalyticsManager(db)
    return manager.get_performance_summary(days)

@app.get("/analytics/sector-analysis")
def get_analytics_sector_analysis(db: Session = Depends(get_db)):
    """Get sector-wise analysis"""
    manager = AnalyticsManager(db)
    return manager.get_sector_analysis()

@app.get("/analytics/trading-activity")
def get_analytics_trading_activity(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Get trading activity summary"""
    manager = AnalyticsManager(db)
    return manager.get_trading_activity(days)

# ==================== WATCHLIST ====================

@app.get("/watchlist", response_model=List[WatchlistResponse])
def get_watchlist(
    account_id: Optional[int] = None,
    category: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """Get watchlist items"""
    manager = WatchlistManager(db)
    return manager.get_watchlist(account_id, category, include_inactive)

@app.get("/watchlist/{account_id}", response_model=List[WatchlistResponse])
def get_account_watchlist(
    account_id: int,
    category: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """Get watchlist for a specific account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = WatchlistManager(db)
    return manager.get_watchlist(account_id, category, include_inactive)

@app.post("/watchlist", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(account_id: int, item: WatchlistCreate, db: Session = Depends(get_db)):
    """Add a stock to watchlist"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = WatchlistManager(db)
    try:
        return manager.add_to_watchlist(account_id, item.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/watchlist/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist_item(
    watchlist_id: int,
    account_id: int,
    update_data: WatchlistUpdate,
    db: Session = Depends(get_db)
):
    """Update a watchlist item"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = WatchlistManager(db)
    try:
        return manager.update_watchlist_item(account_id, watchlist_id, update_data.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/watchlist/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(watchlist_id: int, account_id: int, db: Session = Depends(get_db)):
    """Remove a stock from watchlist"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = WatchlistManager(db)
    try:
        manager.remove_from_watchlist(account_id, watchlist_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/watchlist/bulk")
def bulk_add_to_watchlist(account_id: int, request: WatchlistBulkRequest, db: Session = Depends(get_db)):
    """Add multiple stocks to watchlist"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = WatchlistManager(db)
    return manager.bulk_add_to_watchlist(account_id, [s.model_dump() for s in request.stock_list])

@app.post("/watchlist/update-prices")
def update_watchlist_prices(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Update current prices for all watchlist items"""
    manager = WatchlistManager(db)
    return manager.update_all_prices(account_id)

@app.get("/watchlist/summary", response_model=WatchlistSummary)
def get_watchlist_summary(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get watchlist summary statistics"""
    manager = WatchlistManager(db)
    return manager.get_watchlist_summary(account_id)

@app.get("/watchlist/categories")
def get_watchlist_categories(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all unique categories in watchlist"""
    manager = WatchlistManager(db)
    return {"categories": manager.get_categories(account_id)}

@app.get("/watchlist/search", response_model=List[WatchlistResponse])
def search_watchlist(account_id: int, search_term: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Search watchlist by stock symbol or notes"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = WatchlistManager(db)
    return manager.search_watchlist(account_id, search_term)

@app.get("/watchlist/price-targets", response_model=List[PriceTargetItem])
def get_price_targets(account_id: int, db: Session = Depends(get_db)):
    """Get stocks that are near their target buy/sell prices (within 5%)"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    manager = WatchlistManager(db)
    return manager.get_price_targets(account_id)

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
