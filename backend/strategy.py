"""
Strategy Module for pyPortMan
Comprehensive trading strategy framework with predefined strategies
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json


class StrategyType(Enum):
    """Types of trading strategies"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"
    POSITIONAL = "positional"


class TimeFrame(Enum):
    """Trading timeframes"""
    INTRADAY_1MIN = "1min"
    INTRADAY_5MIN = "5min"
    INTRADAY_15MIN = "15min"
    INTRADAY_30MIN = "30min"
    INTRADAY_1HOUR = "1hour"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class StrategySignal:
    """Represents a trading signal"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    strength: float  # 0-1, confidence level
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy"""
    name: str
    strategy_type: StrategyType
    timeframe: TimeFrame
    risk_per_trade: float = 2.0  # % of capital
    max_positions: int = 5
    position_size: float = 10.0  # % of capital per position
    stop_loss_percent: Optional[float] = None
    target_percent: Optional[float] = None
    trailing_stop_percent: Optional[float] = None
    pyramiding: bool = False
    max_pyramiding_levels: int = 3
    parameters: Dict = field(default_factory=dict)


class BaseStrategy:
    """Base class for all trading strategies"""

    def __init__(self, config: StrategyConfig):
        """
        Initialize strategy with configuration

        Args:
            config: StrategyConfig object
        """
        self.config = config
        self.name = config.name
        self.strategy_type = config.strategy_type
        self.timeframe = config.timeframe

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Generate trading signals from market data

        Args:
            data: DataFrame with OHLCV data

        Returns:
            List of StrategySignal objects
        """
        raise NotImplementedError("Subclasses must implement generate_signals")

    def validate_signal(self, signal: StrategySignal) -> bool:
        """
        Validate a trading signal

        Args:
            signal: StrategySignal to validate

        Returns:
            True if signal is valid
        """
        if signal.action not in ['BUY', 'SELL', 'HOLD']:
            return False

        if signal.strength < 0 or signal.strength > 1:
            return False

        if signal.action in ['BUY', 'SELL']:
            if signal.entry_price is None or signal.entry_price <= 0:
                return False

        return True

    def calculate_position_size(self, capital: float, price: float) -> int:
        """
        Calculate position size based on strategy config

        Args:
            capital: Available capital
            price: Current price

        Returns:
            Quantity to trade
        """
        position_value = capital * (self.config.position_size / 100)
        quantity = int(position_value / price)
        return max(1, quantity)


# ==================== TREND FOLLOWING STRATEGIES ====================

class MovingAverageCrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.fast_period = config.parameters.get('fast_period', 10)
        self.slow_period = config.parameters.get('slow_period', 20)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.slow_period + 1:
            return []

        signals = []

        # Calculate moving averages
        data = data.copy()
        data['fast_ma'] = data['close'].rolling(window=self.fast_period).mean()
        data['slow_ma'] = data['close'].rolling(window=self.slow_period).mean()

        current = data.iloc[-1]
        previous = data.iloc[-2]

        # Check for crossovers
        if (previous['fast_ma'] <= previous['slow_ma']) and (current['fast_ma'] > current['slow_ma']):
            # Bullish crossover
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.8,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason=f'Fast MA ({self.fast_period}) crossed above Slow MA ({self.slow_period})',
                metadata={'fast_ma': current['fast_ma'], 'slow_ma': current['slow_ma']}
            )
            signals.append(signal)

        elif (previous['fast_ma'] >= previous['slow_ma']) and (current['fast_ma'] < current['slow_ma']):
            # Bearish crossover
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.8,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason=f'Fast MA ({self.fast_period}) crossed below Slow MA ({self.slow_period})',
                metadata={'fast_ma': current['fast_ma'], 'slow_ma': current['slow_ma']}
            )
            signals.append(signal)

        return signals


class TripleMovingAverageStrategy(BaseStrategy):
    """Triple Moving Average Strategy (Fast, Medium, Slow)"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.fast_period = config.parameters.get('fast_period', 5)
        self.medium_period = config.parameters.get('medium_period', 15)
        self.slow_period = config.parameters.get('slow_period', 30)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.slow_period + 1:
            return []

        signals = []

        # Calculate moving averages
        data = data.copy()
        data['fast_ma'] = data['close'].rolling(window=self.fast_period).mean()
        data['medium_ma'] = data['close'].rolling(window=self.medium_period).mean()
        data['slow_ma'] = data['close'].rolling(window=self.slow_period).mean()

        current = data.iloc[-1]
        previous = data.iloc[-2]

        # Triple alignment check
        if (current['fast_ma'] > current['medium_ma'] > current['slow_ma'] and
            previous['fast_ma'] <= previous['medium_ma']):
            # Bullish alignment
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.9,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason='Triple MA bullish alignment',
                metadata={
                    'fast_ma': current['fast_ma'],
                    'medium_ma': current['medium_ma'],
                    'slow_ma': current['slow_ma']
                }
            )
            signals.append(signal)

        elif (current['fast_ma'] < current['medium_ma'] < current['slow_ma'] and
              previous['fast_ma'] >= previous['medium_ma']):
            # Bearish alignment
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.9,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason='Triple MA bearish alignment',
                metadata={
                    'fast_ma': current['fast_ma'],
                    'medium_ma': current['medium_ma'],
                    'slow_ma': current['slow_ma']
                }
            )
            signals.append(signal)

        return signals


class ADXTrendStrategy(BaseStrategy):
    """ADX-based Trend Following Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.adx_period = config.parameters.get('adx_period', 14)
        self.di_period = config.parameters.get('di_period', 14)
        self.adx_threshold = config.parameters.get('adx_threshold', 25)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.adx_period + self.di_period + 1:
            return []

        signals = []

        # Calculate ADX and DI
        data = data.copy()

        # Calculate True Range
        high = data['high']
        low = data['low']
        close_prev = data['close'].shift(1)

        tr = pd.concat([
            high - low,
            (high - close_prev).abs(),
            (low - close_prev).abs()
        ], axis=1).max(axis=1)

        # Calculate directional movements
        high_prev = high.shift(1)
        low_prev = low.shift(1)

        plus_dm = np.where(high - high_prev > low_prev - low, high - high_prev, 0)
        minus_dm = np.where(low_prev - low > high - high_prev, low_prev - low, 0)

        # Smooth using Wilder's method
        def wilder_smooth(data, period):
            smoothed = np.zeros_like(data)
            smoothed[0] = data[0]
            for i in range(1, len(data)):
                smoothed[i] = smoothed[i - 1] + (data[i] - smoothed[i - 1]) / period
            return smoothed

        atr = wilder_smooth(tr.values, self.adx_period)
        plus_dm_smooth = wilder_smooth(plus_dm, self.di_period)
        minus_dm_smooth = wilder_smooth(minus_dm, self.di_period)

        # Calculate DI
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)

        # Calculate DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        dx = np.nan_to_num(dx, nan=0)

        # Calculate ADX
        adx = wilder_smooth(dx, self.adx_period)

        current = data.iloc[-1]
        current_adx = adx[-1]
        current_plus_di = plus_di[-1]
        current_minus_di = minus_di[-1]

        # Generate signals based on ADX and DI
        if current_adx > self.adx_threshold:
            if current_plus_di > current_minus_di:
                signal = StrategySignal(
                    symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                    action='BUY',
                    strength=min(0.5 + (current_adx - self.adx_threshold) / 50, 1.0),
                    entry_price=current['close'],
                    stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                    target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                    reason=f'ADX ({current_adx:.1f}) shows strong uptrend, +DI > -DI',
                    metadata={
                        'adx': current_adx,
                        'plus_di': current_plus_di,
                        'minus_di': current_minus_di
                    }
                )
                signals.append(signal)
            else:
                signal = StrategySignal(
                    symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                    action='SELL',
                    strength=min(0.5 + (current_adx - self.adx_threshold) / 50, 1.0),
                    entry_price=current['close'],
                    stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                    target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                    reason=f'ADX ({current_adx:.1f}) shows strong downtrend, -DI > +DI',
                    metadata={
                        'adx': current_adx,
                        'plus_di': current_plus_di,
                        'minus_di': current_minus_di
                    }
                )
                signals.append(signal)

        return signals


# ==================== MEAN REVERSION STRATEGIES ====================

class RSIMeanReversionStrategy(BaseStrategy):
    """RSI-based Mean Reversion Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.oversold = config.parameters.get('oversold', 30)
        self.overbought = config.parameters.get('overbought', 70)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.rsi_period + 1:
            return []

        signals = []

        # Calculate RSI
        data = data.copy()
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]
        previous_rsi = rsi.iloc[-2]
        current = data.iloc[-1]

        # Check for RSI reversals
        if previous_rsi <= self.oversold and current_rsi > self.oversold:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.7 + (self.oversold - previous_rsi) / 100,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason=f'RSI crossed above oversold ({self.oversold})',
                metadata={'rsi': current_rsi}
            )
            signals.append(signal)

        elif previous_rsi >= self.overbought and current_rsi < self.overbought:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.7 + (previous_rsi - self.overbought) / 100,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason=f'RSI crossed below overbought ({self.overbought})',
                metadata={'rsi': current_rsi}
            )
            signals.append(signal)

        return signals


class BollingerBandReversionStrategy(BaseStrategy):
    """Bollinger Band Mean Reversion Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.period = config.parameters.get('period', 20)
        self.std_dev = config.parameters.get('std_dev', 2.0)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.period + 1:
            return []

        signals = []

        # Calculate Bollinger Bands
        data = data.copy()
        sma = data['close'].rolling(window=self.period).mean()
        std = data['close'].rolling(window=self.period).std()

        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)

        current = data.iloc[-1]
        previous = data.iloc[-2]

        # Check for band penetrations
        if previous['close'] >= lower_band.iloc[-2] and current['close'] < lower_band.iloc[-1]:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.75,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=sma.iloc[-1],  # Target is the middle band
                reason='Price crossed below lower Bollinger Band',
                metadata={
                    'upper_band': upper_band.iloc[-1],
                    'middle_band': sma.iloc[-1],
                    'lower_band': lower_band.iloc[-1]
                }
            )
            signals.append(signal)

        elif previous['close'] <= upper_band.iloc[-2] and current['close'] > upper_band.iloc[-1]:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.75,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=sma.iloc[-1],  # Target is the middle band
                reason='Price crossed above upper Bollinger Band',
                metadata={
                    'upper_band': upper_band.iloc[-1],
                    'middle_band': sma.iloc[-1],
                    'lower_band': lower_band.iloc[-1]
                }
            )
            signals.append(signal)

        return signals


class MeanReversionStrategy(BaseStrategy):
    """Statistical Mean Reversion Strategy using Z-score"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.lookback_period = config.parameters.get('lookback_period', 20)
        self.z_threshold = config.parameters.get('z_threshold', 2.0)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.lookback_period + 1:
            return []

        signals = []

        # Calculate mean and standard deviation
        data = data.copy()
        rolling_mean = data['close'].rolling(window=self.lookback_period).mean()
        rolling_std = data['close'].rolling(window=self.lookback_period).std()

        # Calculate Z-score
        z_score = (data['close'] - rolling_mean) / rolling_std

        current_z = z_score.iloc[-1]
        previous_z = z_score.iloc[-2]
        current = data.iloc[-1]

        # Check for Z-score reversals
        if previous_z <= -self.z_threshold and current_z > -self.z_threshold:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=min(0.5 + abs(previous_z) / 10, 1.0),
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=rolling_mean.iloc[-1],
                reason=f'Z-score crossed above -{self.z_threshold}',
                metadata={'z_score': current_z, 'mean': rolling_mean.iloc[-1]}
            )
            signals.append(signal)

        elif previous_z >= self.z_threshold and current_z < self.z_threshold:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=min(0.5 + abs(previous_z) / 10, 1.0),
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=rolling_mean.iloc[-1],
                reason=f'Z-score crossed below {self.z_threshold}',
                metadata={'z_score': current_z, 'mean': rolling_mean.iloc[-1]}
            )
            signals.append(signal)

        return signals


# ==================== MOMENTUM STRATEGIES ====================

class RSIMomentumStrategy(BaseStrategy):
    """RSI Momentum Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.momentum_threshold = config.parameters.get('momentum_threshold', 50)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.rsi_period + 1:
            return []

        signals = []

        # Calculate RSI
        data = data.copy()
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]
        previous_rsi = rsi.iloc[-2]
        current = data.iloc[-1]

        # Momentum signals
        if previous_rsi < self.momentum_threshold and current_rsi > self.momentum_threshold:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.6 + (current_rsi - self.momentum_threshold) / 100,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason=f'RSI momentum crossed above {self.momentum_threshold}',
                metadata={'rsi': current_rsi}
            )
            signals.append(signal)

        elif previous_rsi > (100 - self.momentum_threshold) and current_rsi < (100 - self.momentum_threshold):
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.6 + ((100 - self.momentum_threshold) - current_rsi) / 100,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason=f'RSI momentum crossed below {100 - self.momentum_threshold}',
                metadata={'rsi': current_rsi}
            )
            signals.append(signal)

        return signals


class MACDMomentumStrategy(BaseStrategy):
    """MACD Momentum Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.fast_period = config.parameters.get('fast_period', 12)
        self.slow_period = config.parameters.get('slow_period', 26)
        self.signal_period = config.parameters.get('signal_period', 9)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.slow_period + self.signal_period + 1:
            return []

        signals = []

        # Calculate MACD
        data = data.copy()
        ema_fast = data['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.slow_period, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = macd_line.iloc[-1]
        previous_macd = macd_line.iloc[-2]
        current_signal = signal_line.iloc[-1]
        previous_signal = signal_line.iloc[-2]
        current_hist = histogram.iloc[-1]
        previous_hist = histogram.iloc[-2]
        current = data.iloc[-1]

        # MACD crossover signals
        if (previous_macd <= previous_signal) and (current_macd > current_signal):
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.8,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason='MACD crossed above signal line',
                metadata={
                    'macd': current_macd,
                    'signal': current_signal,
                    'histogram': current_hist
                }
            )
            signals.append(signal)

        elif (previous_macd >= previous_signal) and (current_macd < current_signal):
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.8,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason='MACD crossed below signal line',
                metadata={
                    'macd': current_macd,
                    'signal': current_signal,
                    'histogram': current_hist
                }
            )
            signals.append(signal)

        # Histogram divergence signals
        elif (previous_hist < 0) and (current_hist > 0):
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.6,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason='MACD histogram turned positive',
                metadata={'histogram': current_hist}
            )
            signals.append(signal)

        elif (previous_hist > 0) and (current_hist < 0):
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.6,
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason='MACD histogram turned negative',
                metadata={'histogram': current_hist}
            )
            signals.append(signal)

        return signals


# ==================== BREAKOUT STRATEGIES ====================

class DonchianBreakoutStrategy(BaseStrategy):
    """Donchian Channel Breakout Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.period = config.parameters.get('period', 20)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.period + 1:
            return []

        signals = []

        # Calculate Donchian Channels
        data = data.copy()
        data['upper_channel'] = data['high'].rolling(window=self.period).max()
        data['lower_channel'] = data['low'].rolling(window=self.period).min()

        current = data.iloc[-1]
        previous = data.iloc[-2]

        # Check for breakouts
        if previous['close'] <= previous['upper_channel'] and current['close'] > current['upper_channel']:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=0.85,
                entry_price=current['close'],
                stop_loss=current['lower_channel'],
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason=f'Price broke above {self.period}-period Donchian channel',
                metadata={
                    'upper_channel': current['upper_channel'],
                    'lower_channel': current['lower_channel']
                }
            )
            signals.append(signal)

        elif previous['close'] >= previous['lower_channel'] and current['close'] < current['lower_channel']:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=0.85,
                entry_price=current['close'],
                stop_loss=current['upper_channel'],
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason=f'Price broke below {self.period}-period Donchian channel',
                metadata={
                    'upper_channel': current['upper_channel'],
                    'lower_channel': current['lower_channel']
                }
            )
            signals.append(signal)

        return signals


class RangeBreakoutStrategy(BaseStrategy):
    """Range Breakout Strategy"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.lookback_period = config.parameters.get('lookback_period', 20)
        self.confirmation_bars = config.parameters.get('confirmation_bars', 1)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < self.lookback_period + self.confirmation_bars:
            return []

        signals = []

        # Calculate range
        data = data.copy()
        data['range_high'] = data['high'].rolling(window=self.lookback_period).max()
        data['range_low'] = data['low'].rolling(window=self.lookback_period).min()

        current = data.iloc[-1]

        # Check for confirmed breakouts
        if current['close'] > current['range_high']:
            # Check for confirmation
            confirmed = True
            for i in range(1, self.confirmation_bars + 1):
                if len(data) > i and data.iloc[-i]['close'] <= data.iloc[-i]['range_high']:
                    confirmed = False
                    break

            if confirmed:
                signal = StrategySignal(
                    symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                    action='BUY',
                    strength=0.8,
                    entry_price=current['close'],
                    stop_loss=current['range_low'],
                    target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                    reason=f'Confirmed breakout above {self.lookback_period}-period range',
                    metadata={
                        'range_high': current['range_high'],
                        'range_low': current['range_low']
                    }
                )
                signals.append(signal)

        elif current['close'] < current['range_low']:
            # Check for confirmation
            confirmed = True
            for i in range(1, self.confirmation_bars + 1):
                if len(data) > i and data.iloc[-i]['close'] >= data.iloc[-i]['range_low']:
                    confirmed = False
                    break

            if confirmed:
                signal = StrategySignal(
                    symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                    action='SELL',
                    strength=0.8,
                    entry_price=current['close'],
                    stop_loss=current['range_high'],
                    target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                    reason=f'Confirmed breakdown below {self.lookback_period}-period range',
                    metadata={
                        'range_high': current['range_high'],
                        'range_low': current['range_low']
                    }
                )
                signals.append(signal)

        return signals


# ==================== COMBINED STRATEGIES ====================

class MultiIndicatorStrategy(BaseStrategy):
    """Multi-Indicator Strategy combining multiple signals"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.indicators = config.parameters.get('indicators', ['rsi', 'macd', 'ma'])
        self.min_signals = config.parameters.get('min_signals', 2)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        if len(data) < 30:
            return []

        signals = []
        buy_votes = 0
        sell_votes = 0
        total_strength = 0

        # RSI signal
        if 'rsi' in self.indicators:
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]

            if current_rsi < 30:
                buy_votes += 1
                total_strength += 0.7
            elif current_rsi > 70:
                sell_votes += 1
                total_strength += 0.7

        # MACD signal
        if 'macd' in self.indicators:
            ema_fast = data['close'].ewm(span=12, adjust=False).mean()
            ema_slow = data['close'].ewm(span=26, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=9, adjust=False).mean()

            if macd_line.iloc[-1] > signal_line.iloc[-1]:
                buy_votes += 1
                total_strength += 0.8
            else:
                sell_votes += 1
                total_strength += 0.8

        # Moving Average signal
        if 'ma' in self.indicators:
            fast_ma = data['close'].rolling(window=10).mean()
            slow_ma = data['close'].rolling(window=20).mean()

            if fast_ma.iloc[-1] > slow_ma.iloc[-1]:
                buy_votes += 1
                total_strength += 0.6
            else:
                sell_votes += 1
                total_strength += 0.6

        # Generate signal based on votes
        current = data.iloc[-1]
        avg_strength = total_strength / max(buy_votes + sell_votes, 1)

        if buy_votes >= self.min_signals and buy_votes > sell_votes:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='BUY',
                strength=min(avg_strength, 1.0),
                entry_price=current['close'],
                stop_loss=current['close'] * (1 - (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 + (self.config.target_percent or 10) / 100),
                reason=f'{buy_votes} indicators bullish',
                metadata={'buy_votes': buy_votes, 'sell_votes': sell_votes}
            )
            signals.append(signal)

        elif sell_votes >= self.min_signals and sell_votes > buy_votes:
            signal = StrategySignal(
                symbol=data.index[-1] if hasattr(data.index[-1], '__str__') else 'default',
                action='SELL',
                strength=min(avg_strength, 1.0),
                entry_price=current['close'],
                stop_loss=current['close'] * (1 + (self.config.stop_loss_percent or 5) / 100),
                target_price=current['close'] * (1 - (self.config.target_percent or 10) / 100),
                reason=f'{sell_votes} indicators bearish',
                metadata={'buy_votes': buy_votes, 'sell_votes': sell_votes}
            )
            signals.append(signal)

        return signals


# ==================== STRATEGY FACTORY ====================

class StrategyFactory:
    """Factory for creating strategy instances"""

    _strategies = {
        'ma_crossover': MovingAverageCrossoverStrategy,
        'triple_ma': TripleMovingAverageStrategy,
        'adx_trend': ADXTrendStrategy,
        'rsi_reversion': RSIMeanReversionStrategy,
        'bb_reversion': BollingerBandReversionStrategy,
        'mean_reversion': MeanReversionStrategy,
        'rsi_momentum': RSIMomentumStrategy,
        'macd_momentum': MACDMomentumStrategy,
        'donchian_breakout': DonchianBreakoutStrategy,
        'range_breakout': RangeBreakoutStrategy,
        'multi_indicator': MultiIndicatorStrategy,
    }

    @classmethod
    def create_strategy(cls, strategy_name: str, config: StrategyConfig) -> BaseStrategy:
        """
        Create a strategy instance

        Args:
            strategy_name: Name of the strategy
            config: Strategy configuration

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy name is not found
        """
        strategy_class = cls._strategies.get(strategy_name.lower())
        if strategy_class is None:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available strategies: {list(cls._strategies.keys())}")

        return strategy_class(config)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """Get list of available strategy names"""
        return list(cls._strategies.keys())

    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """
        Register a custom strategy

        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        cls._strategies[name.lower()] = strategy_class


# ==================== STRATEGY MANAGER ====================

class StrategyManager:
    """Manager for running multiple strategies"""

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_signals: List[StrategySignal] = []

    def add_strategy(self, name: str, strategy: BaseStrategy):
        """
        Add a strategy to the manager

        Args:
            name: Strategy name
            strategy: Strategy instance
        """
        self.strategies[name] = strategy

    def remove_strategy(self, name: str):
        """
        Remove a strategy from the manager

        Args:
            name: Strategy name
        """
        if name in self.strategies:
            del self.strategies[name]

    def run_all_strategies(self, data: pd.DataFrame) -> Dict[str, List[StrategySignal]]:
        """
        Run all registered strategies

        Args:
            data: Market data

        Returns:
            Dictionary of strategy name to signals
        """
        results = {}
        for name, strategy in self.strategies.items():
            try:
                signals = strategy.generate_signals(data)
                results[name] = signals
            except Exception as e:
                results[name] = []
                print(f"Error running strategy {name}: {e}")

        return results

    def get_consensus_signal(self, data: pd.DataFrame) -> Optional[StrategySignal]:
        """
        Get consensus signal from all strategies

        Args:
            data: Market data

        Returns:
            Consensus signal or None
        """
        all_signals = self.run_all_strategies(data)

        buy_count = 0
        sell_count = 0
        buy_strength = 0
        sell_strength = 0

        for signals in all_signals.values():
            for signal in signals:
                if signal.action == 'BUY':
                    buy_count += 1
                    buy_strength += signal.strength
                elif signal.action == 'SELL':
                    sell_count += 1
                    sell_strength += signal.strength

        if buy_count > sell_count:
            avg_strength = buy_strength / buy_count if buy_count > 0 else 0
            return StrategySignal(
                symbol='consensus',
                action='BUY',
                strength=min(avg_strength, 1.0),
                reason=f'Consensus: {buy_count} BUY vs {sell_count} SELL',
                metadata={'buy_count': buy_count, 'sell_count': sell_count}
            )
        elif sell_count > buy_count:
            avg_strength = sell_strength / sell_count if sell_count > 0 else 0
            return StrategySignal(
                symbol='consensus',
                action='SELL',
                strength=min(avg_strength, 1.0),
                reason=f'Consensus: {sell_count} SELL vs {buy_count} BUY',
                metadata={'buy_count': buy_count, 'sell_count': sell_count}
            )

        return None


# ==================== HELPER FUNCTIONS ====================

def create_default_config(strategy_type: StrategyType) -> StrategyConfig:
    """
    Create default configuration for a strategy type

    Args:
        strategy_type: Type of strategy

    Returns:
        StrategyConfig with default parameters
    """
    configs = {
        StrategyType.TREND_FOLLOWING: StrategyConfig(
            name="Trend Following",
            strategy_type=strategy_type,
            timeframe=TimeFrame.DAILY,
            risk_per_trade=2.0,
            max_positions=5,
            position_size=10.0,
            stop_loss_percent=5.0,
            target_percent=15.0,
            trailing_stop_percent=3.0
        ),
        StrategyType.MEAN_REVERSION: StrategyConfig(
            name="Mean Reversion",
            strategy_type=strategy_type,
            timeframe=TimeFrame.DAILY,
            risk_per_trade=1.5,
            max_positions=8,
            position_size=8.0,
            stop_loss_percent=3.0,
            target_percent=8.0
        ),
        StrategyType.MOMENTUM: StrategyConfig(
            name="Momentum",
            strategy_type=strategy_type,
            timeframe=TimeFrame.DAILY,
            risk_per_trade=2.5,
            max_positions=4,
            position_size=12.0,
            stop_loss_percent=4.0,
            target_percent=20.0,
            trailing_stop_percent=2.0
        ),
        StrategyType.BREAKOUT: StrategyConfig(
            name="Breakout",
            strategy_type=strategy_type,
            timeframe=TimeFrame.DAILY,
            risk_per_trade=2.0,
            max_positions=3,
            position_size=15.0,
            stop_loss_percent=5.0,
            target_percent=25.0,
            trailing_stop_percent=3.0
        ),
        StrategyType.SCALPING: StrategyConfig(
            name="Scalping",
            strategy_type=strategy_type,
            timeframe=TimeFrame.INTRADAY_5MIN,
            risk_per_trade=0.5,
            max_positions=10,
            position_size=5.0,
            stop_loss_percent=0.5,
            target_percent=1.0
        ),
        StrategyType.SWING: StrategyConfig(
            name="Swing",
            strategy_type=strategy_type,
            timeframe=TimeFrame.INTRADAY_1HOUR,
            risk_per_trade=1.5,
            max_positions=6,
            position_size=8.0,
            stop_loss_percent=2.0,
            target_percent=5.0,
            trailing_stop_percent=1.0
        ),
        StrategyType.POSITIONAL: StrategyConfig(
            name="Positional",
            strategy_type=strategy_type,
            timeframe=TimeFrame.WEEKLY,
            risk_per_trade=3.0,
            max_positions=3,
            position_size=20.0,
            stop_loss_percent=10.0,
            target_percent=30.0,
            trailing_stop_percent=5.0
        ),
    }

    return configs.get(strategy_type, StrategyConfig(
        name="Default",
        strategy_type=strategy_type,
        timeframe=TimeFrame.DAILY
    ))


def export_strategy_config(config: StrategyConfig, filepath: str):
    """
    Export strategy configuration to JSON

    Args:
        config: StrategyConfig object
        filepath: Path to save the file
    """
    export_data = {
        'name': config.name,
        'strategy_type': config.strategy_type.value,
        'timeframe': config.timeframe.value,
        'risk_per_trade': config.risk_per_trade,
        'max_positions': config.max_positions,
        'position_size': config.position_size,
        'stop_loss_percent': config.stop_loss_percent,
        'target_percent': config.target_percent,
        'trailing_stop_percent': config.trailing_stop_percent,
        'pyramiding': config.pyramiding,
        'max_pyramiding_levels': config.max_pyramiding_levels,
        'parameters': config.parameters
    }

    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=2)


def import_strategy_config(filepath: str) -> StrategyConfig:
    """
    Import strategy configuration from JSON

    Args:
        filepath: Path to the config file

    Returns:
        StrategyConfig object
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    return StrategyConfig(
        name=data['name'],
        strategy_type=StrategyType(data['strategy_type']),
        timeframe=TimeFrame(data['timeframe']),
        risk_per_trade=data.get('risk_per_trade', 2.0),
        max_positions=data.get('max_positions', 5),
        position_size=data.get('position_size', 10.0),
        stop_loss_percent=data.get('stop_loss_percent'),
        target_percent=data.get('target_percent'),
        trailing_stop_percent=data.get('trailing_stop_percent'),
        pyramiding=data.get('pyramiding', False),
        max_pyramiding_levels=data.get('max_pyramiding_levels', 3),
        parameters=data.get('parameters', {})
    )
