"""
Backtesting Module for pyPortMan
Comprehensive backtesting framework for trading strategies
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json


class OrderType(Enum):
    """Types of orders"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"


class PositionType(Enum):
    """Position types"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Trade:
    """Represents a completed trade"""
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    holding_period_days: int
    entry_reason: str
    exit_reason: str
    stop_loss: Optional[float] = None
    target: Optional[float] = None


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    side: OrderSide
    entry_price: float
    quantity: int
    entry_date: datetime
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_stop: Optional[float] = None


@dataclass
class BacktestResult:
    """Results of a backtest"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    average_win: float
    average_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    average_holding_period: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    initial_capital: float = 100000.0
    commission: float = 0.0  # Per trade commission
    commission_percent: float = 0.0  # Percentage commission
    slippage: float = 0.0  # Slippage in percentage
    position_size_percent: float = 10.0  # Position size as % of capital
    max_positions: int = 10  # Maximum concurrent positions
    stop_loss_percent: Optional[float] = None  # Default stop loss
    target_percent: Optional[float] = None  # Default target
    trailing_stop_percent: Optional[float] = None  # Trailing stop loss
    pyramiding: bool = False  # Allow pyramiding
    pyramiding_levels: int = 3  # Max pyramiding levels
    risk_per_trade: float = 2.0  # Risk per trade in %


class Backtester:
    """
    Comprehensive backtesting engine for trading strategies
    """

    def __init__(self, config: BacktestConfig):
        """
        Initialize backtester with configuration

        Args:
            config: BacktestConfig object with backtesting parameters
        """
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [config.initial_capital]
        self.current_capital = config.initial_capital
        self.peak_equity = config.initial_capital
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy: Callable,
        strategy_params: Optional[Dict] = None
    ) -> BacktestResult:
        """
        Run backtest on historical data

        Args:
            data: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            strategy: Strategy function that returns buy/sell signals
            strategy_params: Optional parameters for the strategy

        Returns:
            BacktestResult object with all backtest metrics
        """
        if strategy_params is None:
            strategy_params = {}

        # Reset state
        self._reset_state()

        # Run strategy on each bar
        for i in range(len(data)):
            current_date = data.index[i] if isinstance(data.index, pd.DatetimeIndex) else datetime.now()
            current_bar = data.iloc[i]

            # Get historical data up to current point
            historical_data = data.iloc[:i + 1]

            # Get strategy signals
            signals = strategy(historical_data, **strategy_params)

            # Process signals
            self._process_signals(signals, current_date, current_bar)

            # Update positions
            self._update_positions(current_date, current_bar)

            # Update equity curve
            self._update_equity(current_date, current_bar)

        # Close all remaining positions
        self._close_all_positions(current_date, current_bar, "End of backtest")

        # Calculate results
        return self._calculate_results()

    def _reset_state(self):
        """Reset backtester state"""
        self.positions = {}
        self.trades = []
        self.equity_curve = [self.config.initial_capital]
        self.current_capital = self.config.initial_capital
        self.peak_equity = self.config.initial_capital
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0

    def _process_signals(self, signals: Dict, date: datetime, bar: pd.Series):
        """
        Process trading signals from strategy

        Args:
            signals: Dictionary with buy/sell signals
            date: Current date
            bar: Current bar data
        """
        for symbol, signal in signals.items():
            if signal.get('action') == 'BUY':
                self._execute_buy(symbol, date, bar, signal)
            elif signal.get('action') == 'SELL':
                self._execute_sell(symbol, date, bar, signal)

    def _execute_buy(self, symbol: str, date: datetime, bar: pd.Series, signal: Dict):
        """
        Execute buy order

        Args:
            symbol: Stock symbol
            date: Current date
            bar: Current bar data
            signal: Signal dictionary with order details
        """
        # Check if we already have a position
        if symbol in self.positions:
            if not self.config.pyramiding:
                return

            # Check pyramiding limit
            if self.positions[symbol].quantity >= self.config.pyramiding_levels:
                return

        # Calculate position size
        price = self._get_execution_price(bar, 'BUY', signal.get('order_type', 'MARKET'))
        position_size = self._calculate_position_size(price)

        if position_size <= 0:
            return

        quantity = int(position_size / price)

        if quantity <= 0:
            return

        # Calculate commission
        commission = self._calculate_commission(price, quantity)

        # Check if we have enough capital
        total_cost = (price * quantity) + commission
        if total_cost > self.current_capital:
            return

        # Create or update position
        if symbol in self.positions:
            # Average in for pyramiding
            existing_pos = self.positions[symbol]
            total_qty = existing_pos.quantity + quantity
            avg_price = ((existing_pos.entry_price * existing_pos.quantity) + (price * quantity)) / total_qty
            existing_pos.quantity = total_qty
            existing_pos.entry_price = avg_price
        else:
            # Create new position
            stop_loss = signal.get('stop_loss')
            target = signal.get('target')

            if self.config.stop_loss_percent and not stop_loss:
                stop_loss = price * (1 - self.config.stop_loss_percent / 100)

            if self.config.target_percent and not target:
                target = price * (1 + self.config.target_percent / 100)

            self.positions[symbol] = Position(
                symbol=symbol,
                side=OrderSide.BUY,
                entry_price=price,
                quantity=quantity,
                entry_date=date,
                stop_loss=stop_loss,
                target=target
            )

        # Update capital
        self.current_capital -= total_cost

    def _execute_sell(self, symbol: str, date: datetime, bar: pd.Series, signal: Dict):
        """
        Execute sell order

        Args:
            symbol: Stock symbol
            date: Current date
            bar: Current bar data
            signal: Signal dictionary with order details
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        price = self._get_execution_price(bar, 'SELL', signal.get('order_type', 'MARKET'))

        # Calculate commission
        commission = self._calculate_commission(price, position.quantity)

        # Calculate P&L
        pnl = (price - position.entry_price) * position.quantity - commission
        pnl_percent = ((price - position.entry_price) / position.entry_price) * 100

        # Create trade record
        trade = Trade(
            entry_date=position.entry_date,
            exit_date=date,
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=price,
            quantity=position.quantity,
            pnl=pnl,
            pnl_percent=pnl_percent,
            holding_period_days=(date - position.entry_date).days,
            entry_reason="Strategy Signal",
            exit_reason=signal.get('reason', 'Strategy Signal'),
            stop_loss=position.stop_loss,
            target=position.target
        )

        self.trades.append(trade)

        # Update capital
        self.current_capital += (price * position.quantity) - commission

        # Remove position
        del self.positions[symbol]

    def _update_positions(self, date: datetime, bar: pd.Series):
        """
        Update open positions, check for stop loss and target hits

        Args:
            date: Current date
            bar: Current bar data
        """
        positions_to_close = []

        for symbol, position in self.positions.items():
            high = bar.get('high', bar.get('close', 0))
            low = bar.get('low', bar.get('close', 0))
            close = bar.get('close', 0)

            # Check stop loss
            if position.stop_loss and low <= position.stop_loss:
                positions_to_close.append((symbol, 'Stop Loss Hit'))
                continue

            # Check target
            if position.target and high >= position.target:
                positions_to_close.append((symbol, 'Target Hit'))
                continue

            # Update trailing stop
            if self.config.trailing_stop_percent:
                new_stop = close * (1 - self.config.trailing_stop_percent / 100)
                if position.trailing_stop is None or new_stop > position.trailing_stop:
                    position.trailing_stop = new_stop
                    position.stop_loss = new_stop

        # Close positions
        for symbol, reason in positions_to_close:
            self._execute_sell(symbol, date, bar, {'action': 'SELL', 'reason': reason})

    def _update_equity(self, date: datetime, bar: pd.Series):
        """
        Update equity curve

        Args:
            date: Current date
            bar: Current bar data
        """
        # Calculate unrealized P&L
        unrealized_pnl = 0.0
        for position in self.positions.values():
            current_price = bar.get('close', 0)
            unrealized_pnl += (current_price - position.entry_price) * position.quantity

        total_equity = self.current_capital + unrealized_pnl
        self.equity_curve.append(total_equity)

        # Update peak and drawdown
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity

        drawdown = self.peak_equity - total_equity
        drawdown_percent = (drawdown / self.peak_equity) * 100 if self.peak_equity > 0 else 0

        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        if drawdown_percent > self.max_drawdown_percent:
            self.max_drawdown_percent = drawdown_percent

    def _close_all_positions(self, date: datetime, bar: pd.Series, reason: str):
        """
        Close all open positions

        Args:
            date: Current date
            bar: Current bar data
            reason: Reason for closing
        """
        symbols = list(self.positions.keys())
        for symbol in symbols:
            self._execute_sell(symbol, date, bar, {'action': 'SELL', 'reason': reason})

    def _get_execution_price(self, bar: pd.Series, side: str, order_type: str) -> float:
        """
        Get execution price based on order type

        Args:
            bar: Current bar data
            side: Order side (BUY/SELL)
            order_type: Order type (MARKET/LIMIT/STOP_LOSS)

        Returns:
            Execution price
        """
        base_price = bar.get('close', 0)

        # Apply slippage
        if self.config.slippage > 0:
            slippage_amount = base_price * (self.config.slippage / 100)
            if side == 'BUY':
                base_price += slippage_amount
            else:
                base_price -= slippage_amount

        return base_price

    def _calculate_position_size(self, price: float) -> float:
        """
        Calculate position size based on risk management rules

        Args:
            price: Current price

        Returns:
            Position size in currency
        """
        # Calculate based on position size percentage
        position_size = self.current_capital * (self.config.position_size_percent / 100)

        # Check max positions constraint
        if len(self.positions) >= self.config.max_positions:
            return 0.0

        return position_size

    def _calculate_commission(self, price: float, quantity: int) -> float:
        """
        Calculate commission for a trade

        Args:
            price: Execution price
            quantity: Quantity

        Returns:
            Total commission
        """
        commission = self.config.commission
        commission += (price * quantity) * (self.config.commission_percent / 100)
        return commission

    def _calculate_results(self) -> BacktestResult:
        """
        Calculate backtest results

        Returns:
            BacktestResult object with all metrics
        """
        if not self.trades:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_pnl_percent=0.0,
                average_win=0.0,
                average_loss=0.0,
                profit_factor=0.0,
                max_drawdown=self.max_drawdown,
                max_drawdown_percent=self.max_drawdown_percent,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                average_holding_period=0.0,
                trades=[],
                equity_curve=self.equity_curve
            )

        # Calculate basic metrics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        total_pnl = sum(t.pnl for t in self.trades)
        total_pnl_percent = (total_pnl / self.config.initial_capital) * 100

        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]

        average_win = np.mean(wins) if wins else 0
        average_loss = np.mean(losses) if losses else 0

        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Calculate Sharpe Ratio
        returns = []
        for i in range(1, len(self.equity_curve)):
            if self.equity_curve[i - 1] > 0:
                returns.append((self.equity_curve[i] - self.equity_curve[i - 1]) / self.equity_curve[i - 1])

        if returns:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

            # Calculate Sortino Ratio (using downside deviation)
            downside_returns = [r for r in returns if r < 0]
            if downside_returns:
                downside_deviation = np.std(downside_returns)
                sortino_ratio = np.mean(returns) / downside_deviation * np.sqrt(252) if downside_deviation > 0 else 0
            else:
                sortino_ratio = sharpe_ratio
        else:
            sharpe_ratio = 0
            sortino_ratio = 0

        # Calculate average holding period
        average_holding_period = np.mean([t.holding_period_days for t in self.trades]) if self.trades else 0

        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            max_drawdown=self.max_drawdown,
            max_drawdown_percent=self.max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            average_holding_period=average_holding_period,
            trades=self.trades,
            equity_curve=self.equity_curve,
            daily_returns=returns
        )


# ==================== STRATEGY FUNCTIONS ====================

def moving_average_crossover_strategy(data: pd.DataFrame, fast_period: int = 10, slow_period: int = 20) -> Dict[str, Dict]:
    """
    Simple Moving Average Crossover Strategy

    Args:
        data: Historical OHLCV data
        fast_period: Fast MA period
        slow_period: Slow MA period

    Returns:
        Dictionary with buy/sell signals
    """
    if len(data) < slow_period:
        return {}

    signals = {}

    # Calculate moving averages
    data = data.copy()
    data['fast_ma'] = data['close'].rolling(window=fast_period).mean()
    data['slow_ma'] = data['close'].rolling(window=slow_period).mean()

    # Get last two rows
    if len(data) < 2:
        return {}

    current = data.iloc[-1]
    previous = data.iloc[-2]

    # Check for crossover
    if (previous['fast_ma'] <= previous['slow_ma']) and (current['fast_ma'] > current['slow_ma']):
        signals['default'] = {
            'action': 'BUY',
            'reason': 'Fast MA crossed above Slow MA',
            'order_type': 'MARKET'
        }
    elif (previous['fast_ma'] >= previous['slow_ma']) and (current['fast_ma'] < current['slow_ma']):
        signals['default'] = {
            'action': 'SELL',
            'reason': 'Fast MA crossed below Slow MA',
            'order_type': 'MARKET'
        }

    return signals


def rsi_strategy(data: pd.DataFrame, period: int = 14, oversold: float = 30, overbought: float = 70) -> Dict[str, Dict]:
    """
    RSI-based Strategy

    Args:
        data: Historical OHLCV data
        period: RSI period
        oversold: Oversold threshold
        overbought: Overbought threshold

    Returns:
        Dictionary with buy/sell signals
    """
    if len(data) < period + 1:
        return {}

    signals = {}

    # Calculate RSI
    data = data.copy()
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    current_rsi = rsi.iloc[-1]
    previous_rsi = rsi.iloc[-2]

    # Check for RSI signals
    if previous_rsi <= oversold and current_rsi > oversold:
        signals['default'] = {
            'action': 'BUY',
            'reason': f'RSI crossed above oversold ({oversold})',
            'order_type': 'MARKET'
        }
    elif previous_rsi >= overbought and current_rsi < overbought:
        signals['default'] = {
            'action': 'SELL',
            'reason': f'RSI crossed below overbought ({overbought})',
            'order_type': 'MARKET'
        }

    return signals


def bollinger_band_strategy(data: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Dict[str, Dict]:
    """
    Bollinger Band Strategy

    Args:
        data: Historical OHLCV data
        period: Period for calculation
        std_dev: Standard deviation multiplier

    Returns:
        Dictionary with buy/sell signals
    """
    if len(data) < period:
        return {}

    signals = {}

    # Calculate Bollinger Bands
    data = data.copy()
    sma = data['close'].rolling(window=period).mean()
    std = data['close'].rolling(window=period).std()

    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)

    current = data.iloc[-1]
    previous = data.iloc[-2]

    # Check for band penetration
    if previous['close'] >= lower_band.iloc[-2] and current['close'] < lower_band.iloc[-1]:
        signals['default'] = {
            'action': 'BUY',
            'reason': 'Price crossed below lower Bollinger Band',
            'order_type': 'MARKET'
        }
    elif previous['close'] <= upper_band.iloc[-2] and current['close'] > upper_band.iloc[-1]:
        signals['default'] = {
            'action': 'SELL',
            'reason': 'Price crossed above upper Bollinger Band',
            'order_type': 'MARKET'
        }

    return signals


def macd_strategy(data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, Dict]:
    """
    MACD Strategy

    Args:
        data: Historical OHLCV data
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period

    Returns:
        Dictionary with buy/sell signals
    """
    if len(data) < slow_period + signal_period:
        return {}

    signals = {}

    # Calculate MACD
    data = data.copy()
    ema_fast = data['close'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow_period, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    current_macd = macd_line.iloc[-1]
    previous_macd = macd_line.iloc[-2]
    current_signal = signal_line.iloc[-1]
    previous_signal = signal_line.iloc[-2]

    # Check for MACD crossover
    if (previous_macd <= previous_signal) and (current_macd > current_signal):
        signals['default'] = {
            'action': 'BUY',
            'reason': 'MACD crossed above signal line',
            'order_type': 'MARKET'
        }
    elif (previous_macd >= previous_signal) and (current_macd < current_signal):
        signals['default'] = {
            'action': 'SELL',
            'reason': 'MACD crossed below signal line',
            'order_type': 'MARKET'
        }

    return signals


def multi_indicator_strategy(
    data: pd.DataFrame,
    ma_fast: int = 10,
    ma_slow: int = 20,
    rsi_period: int = 14,
    rsi_oversold: float = 30,
    rsi_overbought: float = 70
) -> Dict[str, Dict]:
    """
    Multi-Indicator Strategy combining MA and RSI

    Args:
        data: Historical OHLCV data
        ma_fast: Fast MA period
        ma_slow: Slow MA period
        rsi_period: RSI period
        rsi_oversold: RSI oversold threshold
        rsi_overbought: RSI overbought threshold

    Returns:
        Dictionary with buy/sell signals
    """
    if len(data) < max(ma_slow, rsi_period) + 1:
        return {}

    signals = {}

    # Calculate indicators
    data = data.copy()
    data['fast_ma'] = data['close'].rolling(window=ma_fast).mean()
    data['slow_ma'] = data['close'].rolling(window=ma_slow).mean()

    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    current = data.iloc[-1]
    previous = data.iloc[-2]
    current_rsi = rsi.iloc[-1]

    # Combined signals
    ma_bullish = current['fast_ma'] > current['slow_ma']
    ma_bearish = current['fast_ma'] < current['slow_ma']
    rsi_oversold_signal = current_rsi < rsi_oversold
    rsi_overbought_signal = current_rsi > rsi_overbought

    if ma_bullish and rsi_oversold_signal:
        signals['default'] = {
            'action': 'BUY',
            'reason': 'Bullish MA with oversold RSI',
            'order_type': 'MARKET'
        }
    elif ma_bearish and rsi_overbought_signal:
        signals['default'] = {
            'action': 'SELL',
            'reason': 'Bearish MA with overbought RSI',
            'order_type': 'MARKET'
        }

    return signals


# ==================== BACKTESTING HELPERS ====================

def prepare_backtest_data(prices: List[float], dates: Optional[List[datetime]] = None) -> pd.DataFrame:
    """
    Prepare data for backtesting

    Args:
        prices: List of closing prices
        dates: Optional list of dates

    Returns:
        DataFrame with OHLCV data
    """
    if dates is None:
        dates = [datetime.now() - timedelta(days=len(prices) - i) for i in range(len(prices))]

    df = pd.DataFrame({
        'close': prices,
        'open': prices,  # Using close as proxy for open
        'high': prices,  # Using close as proxy for high
        'low': prices,   # Using close as proxy for low
        'volume': [100000] * len(prices)  # Default volume
    }, index=dates)

    return df


def run_strategy_backtest(
    prices: List[float],
    strategy: Callable,
    strategy_params: Optional[Dict] = None,
    config: Optional[BacktestConfig] = None
) -> BacktestResult:
    """
    Convenience function to run a strategy backtest

    Args:
        prices: List of closing prices
        strategy: Strategy function
        strategy_params: Strategy parameters
        config: Backtest configuration

    Returns:
        BacktestResult object
    """
    if config is None:
        config = BacktestConfig()

    data = prepare_backtest_data(prices)
    backtester = Backtester(config)
    return backtester.run_backtest(data, strategy, strategy_params)


def compare_strategies(
    prices: List[float],
    strategies: Dict[str, Tuple[Callable, Dict]],
    config: Optional[BacktestConfig] = None
) -> Dict[str, BacktestResult]:
    """
    Compare multiple strategies

    Args:
        prices: List of closing prices
        strategies: Dictionary of strategy name to (strategy_func, params) tuples
        config: Backtest configuration

    Returns:
        Dictionary of strategy results
    """
    if config is None:
        config = BacktestConfig()

    results = {}
    for name, (strategy, params) in strategies.items():
        results[name] = run_strategy_backtest(prices, strategy, params, config)

    return results


def generate_backtest_report(result: BacktestResult, strategy_name: str = "Strategy") -> str:
    """
    Generate a human-readable backtest report

    Args:
        result: BacktestResult object
        strategy_name: Name of the strategy

    Returns:
        Formatted report string
    """
    report = f"""
{'=' * 60}
BACKTEST REPORT: {strategy_name}
{'=' * 60}

PERFORMANCE METRICS:
--------------------
Total Trades: {result.total_trades}
Winning Trades: {result.winning_trades}
Losing Trades: {result.losing_trades}
Win Rate: {result.win_rate:.2f}%

PROFIT & LOSS:
--------------
Total P&L: ₹{result.total_pnl:,.2f}
Total P&L %: {result.total_pnl_percent:.2f}%
Average Win: ₹{result.average_win:,.2f}
Average Loss: ₹{result.average_loss:,.2f}
Profit Factor: {result.profit_factor:.2f}

RISK METRICS:
-------------
Max Drawdown: ₹{result.max_drawdown:,.2f}
Max Drawdown %: {result.max_drawdown_percent:.2f}%
Sharpe Ratio: {result.sharpe_ratio:.2f}
Sortino Ratio: {result.sortino_ratio:.2f}

OTHER METRICS:
--------------
Average Holding Period: {result.average_holding_period:.1f} days
Initial Capital: ₹{result.equity_curve[0]:,.2f}
Final Equity: ₹{result.equity_curve[-1]:,.2f}

{'=' * 60}
"""
    return report


def export_backtest_results(result: BacktestResult, filepath: str):
    """
    Export backtest results to JSON file

    Args:
        result: BacktestResult object
        filepath: Path to save the file
    """
    export_data = {
        'total_trades': result.total_trades,
        'winning_trades': result.winning_trades,
        'losing_trades': result.losing_trades,
        'win_rate': result.win_rate,
        'total_pnl': result.total_pnl,
        'total_pnl_percent': result.total_pnl_percent,
        'average_win': result.average_win,
        'average_loss': result.average_loss,
        'profit_factor': result.profit_factor,
        'max_drawdown': result.max_drawdown,
        'max_drawdown_percent': result.max_drawdown_percent,
        'sharpe_ratio': result.sharpe_ratio,
        'sortino_ratio': result.sortino_ratio,
        'average_holding_period': result.average_holding_period,
        'equity_curve': result.equity_curve,
        'trades': [
            {
                'entry_date': t.entry_date.isoformat(),
                'exit_date': t.exit_date.isoformat(),
                'symbol': t.symbol,
                'side': t.side.value,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'quantity': t.quantity,
                'pnl': t.pnl,
                'pnl_percent': t.pnl_percent,
                'holding_period_days': t.holding_period_days,
                'entry_reason': t.entry_reason,
                'exit_reason': t.exit_reason,
                'stop_loss': t.stop_loss,
                'target': t.target
            }
            for t in result.trades
        ]
    }

    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=2)
