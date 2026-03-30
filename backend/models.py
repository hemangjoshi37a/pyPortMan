"""
Database Models for pyPortMan Backend
SQLAlchemy models for storing accounts, holdings, orders, positions, and portfolio snapshots
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Account(Base):
    """Zerodha account information"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Account name/alias
    account_id = Column(String(50), unique=True, nullable=False, index=True)  # Zerodha user ID
    api_key = Column(String(100), nullable=False)
    api_secret = Column(String(100), nullable=False)
    access_token = Column(Text, nullable=True)  # Can be long, use Text
    request_token = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # Relationships
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', account_id='{self.account_id}')>"


class Holding(Base):
    """Stock holdings from Zerodha"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)  # Trading symbol
    exchange = Column(String(20), default="NSE")
    qty = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    ltp = Column(Float, nullable=False)  # Last traded price
    current_value = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)
    pnl_percent = Column(Float, nullable=False)
    product = Column(String(20), default="CNC")  # CNC, MIS, etc.
    isin = Column(String(20), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account", back_populates="holdings")

    def __repr__(self):
        return f"<Holding(stock='{self.stock}', qty={self.qty}, pnl={self.pnl})>"


class Order(Base):
    """Order history from Zerodha"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    order_id = Column(String(50), unique=True, nullable=False, index=True)  # Zerodha order ID
    stock = Column(String(50), nullable=False)
    exchange = Column(String(20), default="NSE")
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    order_type = Column(String(20), nullable=False)  # MARKET, LIMIT, SL, SL-M
    transaction_type = Column(String(10), nullable=False)  # BUY, SELL
    status = Column(String(20), nullable=False)  # COMPLETE, REJECTED, CANCELLED, etc.
    product = Column(String(20), default="CNC")
    validity = Column(String(20), default="DAY")
    variety = Column(String(20), default="regular")  # regular, amo, bo, co
    placed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account", back_populates="orders")

    def __repr__(self):
        return f"<Order(order_id='{self.order_id}', stock='{self.stock}', status='{self.status}')>"


class Position(Base):
    """Intraday positions from Zerodha"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    qty = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    ltp = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)
    pnl_percent = Column(Float, nullable=False)
    product = Column(String(20), nullable=False)  # MIS, CO, BO
    product_type = Column(String(20), default="MIS")  # intraday, overnight
    buy_qty = Column(Integer, default=0)
    sell_qty = Column(Integer, default=0)
    buy_avg_price = Column(Float, default=0)
    sell_avg_price = Column(Float, default=0)
    unrealized_pnl = Column(Float, default=0)
    realized_pnl = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account", back_populates="positions")

    def __repr__(self):
        return f"<Position(stock='{self.stock}', qty={self.qty}, pnl={self.pnl})>"


class PortfolioSnapshot(Base):
    """Portfolio value snapshots for equity curve tracking"""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    total_value = Column(Float, nullable=False)
    investment_value = Column(Float, nullable=False)
    day_pnl = Column(Float, nullable=False)
    day_pnl_percent = Column(Float, nullable=False)
    overall_pnl = Column(Float, nullable=False)
    overall_pnl_percent = Column(Float, nullable=False)
    holdings_count = Column(Integer, default=0)
    positions_count = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    account = relationship("Account", back_populates="portfolio_snapshots")

    def __repr__(self):
        return f"<PortfolioSnapshot(account_id={self.account_id}, total_value={self.total_value}, recorded_at={self.recorded_at})>"
