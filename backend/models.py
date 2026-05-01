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


# ==================== NEW FEATURE MODELS ====================


class TrailingStopLoss(Base):
    """Trailing stop-loss orders that auto-adjust as price moves favorably"""
    __tablename__ = "trailing_stop_loss"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    qty = Column(Integer, nullable=False)
    initial_stop_loss = Column(Float, nullable=False)  # Initial SL price
    current_stop_loss = Column(Float, nullable=False)  # Current SL price (trails)
    trail_amount = Column(Float, nullable=False)  # Amount to trail (points or percentage)
    trail_type = Column(String(10), default="POINTS")  # POINTS or PERCENTAGE
    highest_price = Column(Float, default=0)  # Highest price since activation (for long positions)
    lowest_price = Column(Float, default=0)  # Lowest price since activation (for short positions)
    position_type = Column(String(10), default="LONG")  # LONG or SHORT
    status = Column(String(20), default="ACTIVE")  # ACTIVE, TRIGGERED, CANCELLED, EXPIRED
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<TrailingStopLoss(id={self.id}, stock='{self.stock}', current_sl={self.current_stop_loss})>"


class OrderTemplate(Base):
    """Reusable order templates for quick order placement"""
    __tablename__ = "order_templates"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)  # Null = global template
    name = Column(String(100), nullable=False)  # Template name
    description = Column(Text, nullable=True)  # Template description
    stock = Column(String(50), nullable=True)  # Optional stock symbol
    exchange = Column(String(20), default="NSE")
    transaction_type = Column(String(10), nullable=False)  # BUY or SELL
    order_type = Column(String(20), default="MARKET")  # MARKET, LIMIT, SL, SL-M
    product = Column(String(20), default="CNC")  # CNC, MIS, NRML
    variety = Column(String(20), default="regular")  # regular, amo, bo, co
    default_quantity = Column(Integer, default=1)
    default_price = Column(Float, nullable=True)  # For LIMIT orders
    default_stoploss = Column(Float, nullable=True)  # For SL/CO/BO orders
    default_target = Column(Float, nullable=True)  # For BO orders
    validity = Column(String(20), default="DAY")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<OrderTemplate(id={self.id}, name='{self.name}')>"


class ScheduledOrder(Base):
    """Orders scheduled for specific times (pre-market, post-market)"""
    __tablename__ = "scheduled_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    transaction_type = Column(String(10), nullable=False)  # BUY or SELL
    quantity = Column(Integer, nullable=False)
    order_type = Column(String(20), default="MARKET")  # MARKET, LIMIT, SL, SL-M
    product = Column(String(20), default="CNC")  # CNC, MIS, NRML
    price = Column(Float, nullable=True)  # Required for LIMIT orders
    validity = Column(String(20), default="DAY")
    scheduled_time = Column(DateTime, nullable=False)  # When to place the order
    time_type = Column(String(20), default="SPECIFIC")  # SPECIFIC, PRE_MARKET, POST_MARKET
    status = Column(String(20), default="PENDING")  # PENDING, PLACED, FAILED, CANCELLED
    placed_order_id = Column(String(50), nullable=True)  # Order ID when placed
    error_message = Column(Text, nullable=True)  # Error if placement failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<ScheduledOrder(id={self.id}, stock='{self.stock}', scheduled_time={self.scheduled_time})>"


class PartialExitStrategy(Base):
    """Partial exit strategies with multiple exit points"""
    __tablename__ = "partial_exit_strategies"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    position_type = Column(String(10), default="LONG")  # LONG or SHORT
    total_quantity = Column(Integer, nullable=False)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")
    exit_points = relationship("PartialExitPoint", back_populates="strategy", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PartialExitStrategy(id={self.id}, stock='{self.stock}', total_qty={self.total_quantity})>"


class PartialExitPoint(Base):
    """Individual exit points for partial exit strategies"""
    __tablename__ = "partial_exit_points"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("partial_exit_strategies.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)  # Order of execution (1, 2, 3...)
    quantity = Column(Integer, nullable=False)  # Quantity to exit
    quantity_pct = Column(Float, nullable=True)  # Percentage of total quantity
    target_price = Column(Float, nullable=False)  # Target price for this exit
    stop_loss = Column(Float, nullable=True)  # Optional stop-loss for remaining position
    status = Column(String(20), default="PENDING")  # PENDING, EXECUTED, CANCELLED
    executed_at = Column(DateTime, nullable=True)
    order_id = Column(String(50), nullable=True)  # Order ID when executed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    strategy = relationship("PartialExitStrategy", back_populates="exit_points")

    def __repr__(self):
        return f"<PartialExitPoint(id={self.id}, sequence={self.sequence}, qty={self.quantity})>"


class SectorPnL(Base):
    """Sector-wise P&L attribution tracking"""
    __tablename__ = "sector_pnl"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    sector = Column(String(100), nullable=False, index=True)  # Sector name
    stock = Column(String(50), nullable=False)  # Stock symbol
    investment_value = Column(Float, default=0)  # Total investment
    current_value = Column(Float, default=0)  # Current value
    pnl = Column(Float, default=0)  # Profit/Loss
    pnl_percent = Column(Float, default=0)  # P&L percentage
    weight = Column(Float, default=0)  # Weight in portfolio (0-100)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<SectorPnL(sector='{self.sector}', stock='{self.stock}', pnl={self.pnl})>"


class TradingStatistics(Base):
    """Trading statistics for win rate and risk-reward analysis"""
    __tablename__ = "trading_statistics"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    period = Column(String(20), default="DAILY")  # DAILY, WEEKLY, MONTHLY, YEARLY, ALL_TIME
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # Trade counts
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    break_even_trades = Column(Integer, default=0)

    # Win rate
    win_rate = Column(Float, default=0)  # Percentage
    loss_rate = Column(Float, default=0)  # Percentage

    # P&L statistics
    total_pnl = Column(Float, default=0)
    total_profit = Column(Float, default=0)
    total_loss = Column(Float, default=0)
    avg_profit = Column(Float, default=0)
    avg_loss = Column(Float, default=0)

    # Risk-reward
    risk_reward_ratio = Column(Float, default=0)  # Average profit / Average loss
    max_profit = Column(Float, default=0)
    max_loss = Column(Float, default=0)

    # Drawdown
    max_drawdown = Column(Float, default=0)
    max_drawdown_pct = Column(Float, default=0)

    # Other metrics
    avg_holding_period = Column(Float, default=0)  # In hours
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<TradingStatistics(account_id={self.account_id}, period='{self.period}', win_rate={self.win_rate})>"


class DrawdownRecord(Base):
    """Drawdown analysis records"""
    __tablename__ = "drawdown_records"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    peak_value = Column(Float, nullable=False)  # Portfolio value at peak
    trough_value = Column(Float, nullable=False)  # Portfolio value at trough
    drawdown_amount = Column(Float, nullable=False)  # Peak - Trough
    drawdown_pct = Column(Float, nullable=False)  # Drawdown percentage
    peak_date = Column(DateTime, nullable=False)  # Date of peak
    trough_date = Column(DateTime, nullable=False)  # Date of trough
    recovery_date = Column(DateTime, nullable=True)  # Date of recovery (if recovered)
    duration_days = Column(Integer, default=0)  # Duration of drawdown in days
    is_current = Column(Boolean, default=False)  # Is this the current drawdown?
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<DrawdownRecord(account_id={self.account_id}, drawdown_pct={self.drawdown_pct})>"


class CorrelationData(Base):
    """Correlation matrix data for portfolio holdings"""
    __tablename__ = "correlation_data"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock1 = Column(String(50), nullable=False, index=True)
    stock2 = Column(String(50), nullable=False, index=True)
    correlation = Column(Float, nullable=False)  # Correlation coefficient (-1 to 1)
    period_days = Column(Integer, default=30)  # Period used for calculation
    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<CorrelationData(stock1='{self.stock1}', stock2='{self.stock2}', correlation={self.correlation})>"


class TaxReport(Base):
    """Tax reports for monthly/quarterly statements"""
    __tablename__ = "tax_reports"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    report_type = Column(String(20), nullable=False)  # MONTHLY, QUARTERLY, YEARLY
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    report_data = Column(Text, nullable=False)  # JSON string with report data
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<TaxReport(account_id={self.account_id}, report_type='{self.report_type}')>"


class DiscordConfig(Base):
    """Discord alert configuration"""
    __tablename__ = "discord_config"

    id = Column(Integer, primary_key=True, index=True)
    bot_token = Column(String(255), nullable=True)  # Discord bot token
    channel_id = Column(String(100), nullable=True)  # Discord channel ID
    webhook_url = Column(String(500), nullable=True)  # Discord webhook URL
    gtt_alerts_enabled = Column(Boolean, default=True)
    loss_alerts_enabled = Column(Boolean, default=True)
    daily_summary_enabled = Column(Boolean, default=True)
    order_alerts_enabled = Column(Boolean, default=True)
    loss_threshold_pct = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DiscordConfig(id={self.id}, channel_id='{self.channel_id}')>"


class EmailConfig(Base):
    """Email alert configuration"""
    __tablename__ = "email_config"

    id = Column(Integer, primary_key=True, index=True)
    smtp_server = Column(String(255), nullable=False)
    smtp_port = Column(Integer, default=587)
    smtp_username = Column(String(255), nullable=False)
    smtp_password = Column(Text, nullable=True)  # Encrypted
    from_email = Column(String(255), nullable=False)
    to_emails = Column(Text, nullable=True)  # Comma-separated list
    gtt_alerts_enabled = Column(Boolean, default=True)
    loss_alerts_enabled = Column(Boolean, default=True)
    margin_call_alerts_enabled = Column(Boolean, default=True)
    daily_summary_enabled = Column(Boolean, default=True)
    loss_threshold_pct = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailConfig(id={self.id}, from_email='{self.from_email}')>"


class PriceMovementAlert(Base):
    """Alerts for price movements within a time window"""
    __tablename__ = "price_movement_alerts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    movement_type = Column(String(10), nullable=False)  # UP or DOWN
    movement_pct = Column(Float, nullable=False)  # Percentage movement threshold
    time_window_minutes = Column(Integer, default=60)  # Time window in minutes
    base_price = Column(Float, nullable=True)  # Base price for comparison
    base_price_time = Column(DateTime, nullable=True)  # When base price was recorded
    status = Column(String(20), default="ACTIVE")  # ACTIVE, TRIGGERED, CANCELLED
    triggered_at = Column(DateTime, nullable=True)
    triggered_price = Column(Float, nullable=True)
    repeat = Column(Boolean, default=False)
    repeat_interval_minutes = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<PriceMovementAlert(id={self.id}, stock='{self.stock}', movement_pct={self.movement_pct})>"


class VolumeSpikeAlert(Base):
    """Alerts for unusual volume spikes"""
    __tablename__ = "volume_spike_alerts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    avg_volume_period = Column(Integer, default=20)  # Period for average volume (days)
    volume_multiplier = Column(Float, default=2.0)  # Multiplier for spike detection
    min_volume = Column(Integer, default=10000)  # Minimum volume to consider
    status = Column(String(20), default="ACTIVE")  # ACTIVE, TRIGGERED, CANCELLED
    triggered_at = Column(DateTime, nullable=True)
    triggered_volume = Column(Integer, nullable=True)
    avg_volume = Column(Integer, nullable=True)
    repeat = Column(Boolean, default=False)
    repeat_interval_hours = Column(Integer, default=24)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    account = relationship("Account")

    def __repr__(self):
        return f"<VolumeSpikeAlert(id={self.id}, stock='{self.stock}', multiplier={self.volume_multiplier})>"


class NewsItem(Base):
    """News items for watchlist stocks"""
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    source = Column(String(100), nullable=True)  # News source
    published_at = Column(DateTime, nullable=True)
    sentiment = Column(String(20), nullable=True)  # POSITIVE, NEGATIVE, NEUTRAL
    relevance_score = Column(Float, default=0)  # Relevance score (0-1)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<NewsItem(id={self.id}, stock='{self.stock}', title='{self.title[:50]}...')>"


class OrderBookDepth(Base):
    """Order book depth data for market analysis"""
    __tablename__ = "order_book_depth"

    id = Column(Integer, primary_key=True, index=True)
    stock = Column(String(50), nullable=False, index=True)
    exchange = Column(String(20), default="NSE")
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Bid data (buy orders)
    bid_price_1 = Column(Float, nullable=True)
    bid_qty_1 = Column(Integer, nullable=True)
    bid_price_2 = Column(Float, nullable=True)
    bid_qty_2 = Column(Integer, nullable=True)
    bid_price_3 = Column(Float, nullable=True)
    bid_qty_3 = Column(Integer, nullable=True)
    bid_price_4 = Column(Float, nullable=True)
    bid_qty_4 = Column(Integer, nullable=True)
    bid_price_5 = Column(Float, nullable=True)
    bid_qty_5 = Column(Integer, nullable=True)

    # Ask data (sell orders)
    ask_price_1 = Column(Float, nullable=True)
    ask_qty_1 = Column(Integer, nullable=True)
    ask_price_2 = Column(Float, nullable=True)
    ask_qty_2 = Column(Integer, nullable=True)
    ask_price_3 = Column(Float, nullable=True)
    ask_qty_3 = Column(Integer, nullable=True)
    ask_price_4 = Column(Float, nullable=True)
    ask_qty_4 = Column(Integer, nullable=True)
    ask_price_5 = Column(Float, nullable=True)
    ask_qty_5 = Column(Integer, nullable=True)

    # Summary
    total_bid_qty = Column(Integer, default=0)
    total_ask_qty = Column(Integer, default=0)
    spread = Column(Float, default=0)  # Ask - Bid
    spread_pct = Column(Float, default=0)  # Spread as percentage

    def __repr__(self):
        return f"<OrderBookDepth(stock='{self.stock}', spread={self.spread})>"
