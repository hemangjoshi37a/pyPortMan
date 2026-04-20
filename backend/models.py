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

    # Auto-login fields
    password = Column(Text, nullable=True)  # Encrypted Zerodha password
    totp_secret = Column(Text, nullable=True)  # Encrypted TOTP secret
    last_token_refresh = Column(DateTime, nullable=True)  # Last successful auto-refresh
    auto_login_enabled = Column(Boolean, default=False)  # Enable/disable auto-login

    # Relationships
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="account", cascade="all, delete-orphan")
    gtt_orders = relationship("GTTOrder", cascade="all, delete-orphan")
    watchlist = relationship("Watchlist", cascade="all, delete-orphan")

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


class GTTOrder(Base):
    """Good Till Triggered (GTT) orders from Zerodha"""
    __tablename__ = "gtt_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    gtt_id = Column(String(50), unique=True, nullable=False, index=True)  # Zerodha GTT ID
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    qty = Column(Integer, nullable=False)
    buy_price = Column(Float, nullable=False)  # Trigger price for buying
    target_price = Column(Float, nullable=False)  # Sell target
    sl_price = Column(Float, nullable=False)  # Stop loss
    allocation_pct = Column(Float, default=0)  # % of account funds to allocate
    status = Column(String(20), default="ACTIVE")  # ACTIVE, TRIGGERED, CANCELLED, EXPIRED
    trigger_type = Column(String(20), default="TWO_LEG")  # TWO_LEG, SINGLE
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<GTTOrder(gtt_id='{self.gtt_id}', stock='{self.stock}', status='{self.status}')>"


class AlertConfig(Base):
    """Telegram alert configuration"""
    __tablename__ = "alert_config"

    id = Column(Integer, primary_key=True, index=True)
    bot_token = Column(String(255), nullable=True)  # Telegram bot token
    chat_id = Column(String(100), nullable=True)  # Telegram chat ID
    discord_webhook_url = Column(String(500), nullable=True)  # Discord webhook URL
    gtt_alerts_enabled = Column(Boolean, default=True)  # GTT triggered alerts
    loss_alerts_enabled = Column(Boolean, default=True)  # Big loss alerts
    daily_summary_enabled = Column(Boolean, default=True)  # Daily summary alerts
    order_alerts_enabled = Column(Boolean, default=True)  # Order alerts
    loss_threshold_pct = Column(Float, default=5.0)  # Loss threshold percentage
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AlertConfig(id={self.id}, chat_id='{self.chat_id}')>"


class AlertHistory(Base):
    """History of sent alerts"""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False, index=True)  # GTT_TRIGGERED, BIG_LOSS, etc.
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    success = Column(Boolean, default=False)

    def __repr__(self):
        return f"<AlertHistory(id={self.id}, alert_type='{self.alert_type}', success={self.success})>"


class PriceAlert(Base):
    """Custom price alerts on stocks"""
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    alert_type = Column(String(10), nullable=False)  # ABOVE, BELOW
    target_price = Column(Float, nullable=False)
    current_price = Column(Float, default=0)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, TRIGGERED, COMPLETED
    repeat = Column(Boolean, default=False)
    repeat_interval = Column(Integer, default=24)  # Hours
    triggered_count = Column(Integer, default=0)
    triggered_at = Column(DateTime, nullable=True)
    next_trigger_at = Column(DateTime, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<PriceAlert(id={self.id}, stock='{self.stock}', alert_type='{self.alert_type}', target={self.target_price})>"


class Watchlist(Base):
    """Watchlist for tracking stocks of interest"""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    category = Column(String(50), default="Default")  # Category/group name
    notes = Column(Text, nullable=True)  # User notes about the stock
    target_buy_price = Column(Float, nullable=True)  # Desired buy price
    target_sell_price = Column(Float, nullable=True)  # Desired sell price
    current_price = Column(Float, default=0)
    day_change = Column(Float, default=0)
    day_change_pct = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority = show first
    last_price_update = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account", back_populates="watchlist")

    def __repr__(self):
        return f"<Watchlist(id={self.id}, stock='{self.stock}', category='{self.category}')>"


class PnlThresholdAlert(Base):
    """P&L threshold alerts for portfolio monitoring"""
    __tablename__ = "pnl_threshold_alerts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    stock = Column(String(50), nullable=True, index=True)  # Null = all stocks
    profit_threshold_pct = Column(Float, nullable=True)  # Profit threshold percentage
    loss_threshold_pct = Column(Float, nullable=True)  # Loss threshold percentage
    enabled = Column(Boolean, default=True)
    alert_type = Column(String(20), default="BOTH")  # PROFIT, LOSS, or BOTH
    repeat = Column(Boolean, default=False)  # Repeat alert if threshold crossed again
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<PnlThresholdAlert(id={self.id}, stock='{self.stock}', profit_threshold={self.profit_threshold_pct}, loss_threshold={self.loss_threshold_pct})>"


class TechnicalAlertRule(Base):
    """Technical indicator alert rules"""
    __tablename__ = "technical_alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    stock = Column(String(50), nullable=True, index=True)  # Null = all stocks
    exchange = Column(String(20), default="NSE")
    enabled = Column(Boolean, default=True)

    # RSI settings
    rsi_enabled = Column(Boolean, default=False)
    rsi_overbought = Column(Float, default=70.0)
    rsi_oversold = Column(Float, default=30.0)
    rsi_period = Column(Integer, default=14)

    # MACD settings
    macd_enabled = Column(Boolean, default=False)
    macd_fast_period = Column(Integer, default=12)
    macd_slow_period = Column(Integer, default=26)
    macd_signal_period = Column(Integer, default=9)

    # Moving Average settings
    ma_crossover_enabled = Column(Boolean, default=False)
    ma_fast_period = Column(Integer, default=10)
    ma_slow_period = Column(Integer, default=20)

    # Bollinger Bands settings
    bb_enabled = Column(Boolean, default=False)
    bb_period = Column(Integer, default=20)
    bb_std_dev = Column(Float, default=2.0)

    # Volume settings
    volume_enabled = Column(Boolean, default=False)
    volume_avg_period = Column(Integer, default=20)
    volume_multiplier = Column(Float, default=2.0)

    # Notification settings
    notification_channels = Column(String(100), default="telegram")  # telegram, email, sms, webhook (comma-separated)

    last_checked_at = Column(DateTime, nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<TechnicalAlertRule(id={self.id}, stock='{self.stock}', enabled={self.enabled})>"
