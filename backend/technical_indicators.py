"""
Technical Indicators Module for pyPortMan
Comprehensive collection of technical analysis indicators for stock analysis
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class IndicatorType(Enum):
    """Types of technical indicators"""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OSCILLATOR = "oscillator"


@dataclass
class IndicatorResult:
    """Result of a technical indicator calculation"""
    name: str
    values: List[float]
    signals: List[str]  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0-1, confidence level
    description: str


class TechnicalIndicators:
    """
    Comprehensive technical indicators library
    Supports various indicators for trend, momentum, volatility, and volume analysis
    """

    def __init__(self, prices: List[float], volumes: Optional[List[float]] = None):
        """
        Initialize with price data

        Args:
            prices: List of closing prices
            volumes: Optional list of volume values
        """
        self.prices = np.array(prices)
        self.volumes = np.array(volumes) if volumes else None
        self.length = len(prices)

    # ==================== TREND INDICATORS ====================

    def sma(self, period: int = 20) -> np.ndarray:
        """
        Simple Moving Average

        Args:
            period: Number of periods for SMA

        Returns:
            Array of SMA values
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        sma_values = np.convolve(self.prices, np.ones(period) / period, mode='valid')
        result = np.full(self.length, np.nan)
        result[period - 1:] = sma_values
        return result

    def ema(self, period: int = 20) -> np.ndarray:
        """
        Exponential Moving Average

        Args:
            period: Number of periods for EMA

        Returns:
            Array of EMA values
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        multiplier = 2 / (period + 1)
        ema_values = np.zeros(self.length)
        ema_values[0] = self.prices[0]

        for i in range(1, self.length):
            ema_values[i] = (self.prices[i] * multiplier) + (ema_values[i - 1] * (1 - multiplier))

        return ema_values

    def wma(self, period: int = 20) -> np.ndarray:
        """
        Weighted Moving Average (gives more weight to recent prices)

        Args:
            period: Number of periods for WMA

        Returns:
            Array of WMA values
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        weights = np.arange(1, period + 1)
        weights = weights / weights.sum()

        wma_values = np.zeros(self.length)
        for i in range(period - 1, self.length):
            wma_values[i] = np.sum(self.prices[i - period + 1:i + 1] * weights)

        result = np.full(self.length, np.nan)
        result[period - 1:] = wma_values[period - 1:]
        return result

    def hull_ma(self, period: int = 20) -> np.ndarray:
        """
        Hull Moving Average - faster and smoother than traditional MAs

        Args:
            period: Number of periods for HMA

        Returns:
            Array of HMA values
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        half_period = int(period / 2)
        sqrt_period = int(np.sqrt(period))

        wma_half = self.wma(half_period)
        wma_full = self.wma(period)

        raw_hma = 2 * wma_half - wma_full

        # Calculate WMA of raw HMA with sqrt period
        hma_values = np.zeros(self.length)
        weights = np.arange(1, sqrt_period + 1)
        weights = weights / weights.sum()

        for i in range(sqrt_period - 1, self.length):
            hma_values[i] = np.sum(raw_hma[i - sqrt_period + 1:i + 1] * weights)

        result = np.full(self.length, np.nan)
        result[sqrt_period - 1:] = hma_values[sqrt_period - 1:]
        return result

    def vwma(self, period: int = 20) -> np.ndarray:
        """
        Volume Weighted Moving Average

        Args:
            period: Number of periods for VWMA

        Returns:
            Array of VWMA values
        """
        if self.volumes is None:
            raise ValueError("Volume data required for VWMA")

        if self.length < period:
            return np.full(self.length, np.nan)

        vwma_values = np.zeros(self.length)
        for i in range(period - 1, self.length):
            price_volume = self.prices[i - period + 1:i + 1] * self.volumes[i - period + 1:i + 1]
            total_volume = np.sum(self.volumes[i - period + 1:i + 1])
            vwma_values[i] = np.sum(price_volume) / total_volume if total_volume > 0 else np.nan

        result = np.full(self.length, np.nan)
        result[period - 1:] = vwma_values[period - 1:]
        return result

    def macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, np.ndarray]:
        """
        Moving Average Convergence Divergence

        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period

        Returns:
            Dictionary with MACD line, signal line, and histogram
        """
        ema_fast = self.ema(fast_period)
        ema_slow = self.ema(slow_period)

        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema_from_array(macd_line, signal_period)
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def _calculate_ema_from_array(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA from an existing array"""
        multiplier = 2 / (period + 1)
        ema_values = np.zeros_like(data)

        # Find first valid value
        first_valid = np.where(~np.isnan(data))[0]
        if len(first_valid) == 0:
            return np.full_like(data, np.nan)

        start_idx = first_valid[0]
        ema_values[start_idx] = data[start_idx]

        for i in range(start_idx + 1, len(data)):
            if np.isnan(data[i]):
                ema_values[i] = np.nan
            else:
                ema_values[i] = (data[i] * multiplier) + (ema_values[i - 1] * (1 - multiplier))

        return ema_values

    def adx(self, period: int = 14) -> Dict[str, np.ndarray]:
        """
        Average Directional Index - measures trend strength

        Args:
            period: Period for ADX calculation

        Returns:
            Dictionary with ADX, +DI, and -DI values
        """
        if self.length < period + 1:
            return {
                'adx': np.full(self.length, np.nan),
                'plus_di': np.full(self.length, np.nan),
                'minus_di': np.full(self.length, np.nan)
            }

        # Calculate True Range
        high = self.prices  # Assuming prices are closing, using as proxy
        low = self.prices * 0.99  # Proxy for low
        high_prev = np.roll(high, 1)
        low_prev = np.roll(low, 1)
        close_prev = np.roll(self.prices, 1)

        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - close_prev),
                np.abs(low - close_prev)
            )
        )

        # Calculate directional movements
        plus_dm = np.where(high - high_prev > low_prev - low, high - high_prev, 0)
        minus_dm = np.where(low_prev - low > high - high_prev, low_prev - low, 0)

        # Smooth TR, +DM, -DM
        atr = self._smooth_array(tr, period)
        plus_di_smooth = self._smooth_array(plus_dm, period)
        minus_di_smooth = self._smooth_array(minus_dm, period)

        # Calculate +DI and -DI
        plus_di = 100 * (plus_di_smooth / atr)
        minus_di = 100 * (minus_di_smooth / atr)

        # Calculate DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        dx = np.nan_to_num(dx, nan=0)

        # Calculate ADX
        adx = self._smooth_array(dx, period)

        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }

    def _smooth_array(self, data: np.ndarray, period: int) -> np.ndarray:
        """Smooth array using Wilder's smoothing method"""
        smoothed = np.zeros_like(data)
        smoothed[0] = data[0]

        for i in range(1, len(data)):
            smoothed[i] = smoothed[i - 1] + (data[i] - smoothed[i - 1]) / period

        return smoothed

    def parabolic_sar(self, af_start: float = 0.02, af_increment: float = 0.02, af_max: float = 0.2) -> Dict[str, np.ndarray]:
        """
        Parabolic SAR - used to set trailing stop losses

        Args:
            af_start: Starting acceleration factor
            af_increment: Acceleration factor increment
            af_max: Maximum acceleration factor

        Returns:
            Dictionary with SAR values and trend direction
        """
        if self.length < 2:
            return {
                'sar': np.full(self.length, np.nan),
                'trend': np.full(self.length, 0)
            }

        sar = np.zeros(self.length)
        trend = np.zeros(self.length)
        ep = np.zeros(self.length)
        af = np.zeros(self.length)

        # Initialize
        sar[0] = self.prices[0]
        trend[0] = 1  # 1 for uptrend, -1 for downtrend
        ep[0] = self.prices[0]
        af[0] = af_start

        for i in range(1, self.length):
            # Update SAR
            sar[i] = sar[i - 1] + af[i - 1] * (ep[i - 1] - sar[i - 1])

            # Check for trend reversal
            if trend[i - 1] == 1:  # Uptrend
                if self.prices[i] < sar[i]:
                    # Trend reversal to downtrend
                    trend[i] = -1
                    sar[i] = ep[i - 1]  # SAR becomes the previous extreme point
                    ep[i] = self.prices[i]
                    af[i] = af_start
                else:
                    # Continue uptrend
                    trend[i] = 1
                    if self.prices[i] > ep[i - 1]:
                        ep[i] = self.prices[i]
                        af[i] = min(af[i - 1] + af_increment, af_max)
                    else:
                        ep[i] = ep[i - 1]
                        af[i] = af[i - 1]
            else:  # Downtrend
                if self.prices[i] > sar[i]:
                    # Trend reversal to uptrend
                    trend[i] = 1
                    sar[i] = ep[i - 1]
                    ep[i] = self.prices[i]
                    af[i] = af_start
                else:
                    # Continue downtrend
                    trend[i] = -1
                    if self.prices[i] < ep[i - 1]:
                        ep[i] = self.prices[i]
                        af[i] = min(af[i - 1] + af_increment, af_max)
                    else:
                        ep[i] = ep[i - 1]
                        af[i] = af[i - 1]

        return {
            'sar': sar,
            'trend': trend
        }

    # ==================== MOMENTUM INDICATORS ====================

    def rsi(self, period: int = 14) -> np.ndarray:
        """
        Relative Strength Index

        Args:
            period: Period for RSI calculation

        Returns:
            Array of RSI values (0-100)
        """
        if self.length < period + 1:
            return np.full(self.length, np.nan)

        # Calculate price changes
        deltas = np.diff(self.prices)

        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate average gains and losses
        avg_gains = np.zeros(self.length)
        avg_losses = np.zeros(self.length)

        # First average
        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])

        # Subsequent averages using Wilder's smoothing
        for i in range(period + 1, self.length):
            avg_gains[i] = (avg_gains[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_losses[i] = (avg_losses[i - 1] * (period - 1) + losses[i - 1]) / period

        # Calculate RSI
        rs = np.zeros(self.length)
        rsi = np.zeros(self.length)

        for i in range(period, self.length):
            if avg_losses[i] == 0:
                rs[i] = 100
            else:
                rs[i] = avg_gains[i] / avg_losses[i]

            rsi[i] = 100 - (100 / (1 + rs[i]))

        result = np.full(self.length, np.nan)
        result[period:] = rsi[period:]
        return result

    def stochastic(self, k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> Dict[str, np.ndarray]:
        """
        Stochastic Oscillator

        Args:
            k_period: Period for %K
            d_period: Period for %D
            smooth_k: Smoothing period for %K

        Returns:
            Dictionary with %K and %D values
        """
        if self.length < k_period:
            return {
                'k': np.full(self.length, np.nan),
                'd': np.full(self.length, np.nan)
            }

        # Calculate %K
        k_values = np.zeros(self.length)
        for i in range(k_period - 1, self.length):
            window = self.prices[i - k_period + 1:i + 1]
            high = np.max(window)
            low = np.min(window)
            if high == low:
                k_values[i] = 50
            else:
                k_values[i] = 100 * (self.prices[i] - low) / (high - low)

        # Smooth %K
        if smooth_k > 1:
            k_smooth = np.zeros(self.length)
            for i in range(smooth_k - 1, self.length):
                k_smooth[i] = np.mean(k_values[i - smooth_k + 1:i + 1])
            k_values = k_smooth

        # Calculate %D (SMA of %K)
        d_values = np.zeros(self.length)
        for i in range(d_period - 1, self.length):
            d_values[i] = np.mean(k_values[i - d_period + 1:i + 1])

        result_k = np.full(self.length, np.nan)
        result_d = np.full(self.length, np.nan)
        result_k[k_period - 1:] = k_values[k_period - 1:]
        result_d[k_period + d_period - 2:] = d_values[k_period + d_period - 2:]

        return {
            'k': result_k,
            'd': result_d
        }

    def williams_r(self, period: int = 14) -> np.ndarray:
        """
        Williams %R

        Args:
            period: Period for Williams %R

        Returns:
            Array of Williams %R values (-100 to 0)
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        wr_values = np.zeros(self.length)
        for i in range(period - 1, self.length):
            window = self.prices[i - period + 1:i + 1]
            high = np.max(window)
            low = np.min(window)
            if high == low:
                wr_values[i] = -50
            else:
                wr_values[i] = -100 * (high - self.prices[i]) / (high - low)

        result = np.full(self.length, np.nan)
        result[period - 1:] = wr_values[period - 1:]
        return result

    def momentum(self, period: int = 10) -> np.ndarray:
        """
        Momentum Indicator

        Args:
            period: Period for momentum calculation

        Returns:
            Array of momentum values
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        momentum_values = np.zeros(self.length)
        for i in range(period, self.length):
            momentum_values[i] = self.prices[i] - self.prices[i - period]

        result = np.full(self.length, np.nan)
        result[period:] = momentum_values[period:]
        return result

    def roc(self, period: int = 12) -> np.ndarray:
        """
        Rate of Change

        Args:
            period: Period for ROC calculation

        Returns:
            Array of ROC values (percentage)
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        roc_values = np.zeros(self.length)
        for i in range(period, self.length):
            if self.prices[i - period] != 0:
                roc_values[i] = 100 * (self.prices[i] - self.prices[i - period]) / self.prices[i - period]
            else:
                roc_values[i] = 0

        result = np.full(self.length, np.nan)
        result[period:] = roc_values[period:]
        return result

    def cci(self, period: int = 20) -> np.ndarray:
        """
        Commodity Channel Index

        Args:
            period: Period for CCI calculation

        Returns:
            Array of CCI values
        """
        if self.length < period:
            return np.full(self.length, np.nan)

        # Calculate typical price (using closing price as proxy)
        tp = self.prices

        # Calculate SMA of typical price
        sma_tp = self.sma(period)

        # Calculate mean deviation
        md = np.zeros(self.length)
        for i in range(period - 1, self.length):
            window = tp[i - period + 1:i + 1]
            md[i] = np.mean(np.abs(window - sma_tp[i]))

        # Calculate CCI
        cci_values = np.zeros(self.length)
        for i in range(period - 1, self.length):
            if md[i] == 0:
                cci_values[i] = 0
            else:
                cci_values[i] = (tp[i] - sma_tp[i]) / (0.015 * md[i])

        result = np.full(self.length, np.nan)
        result[period - 1:] = cci_values[period - 1:]
        return result

    # ==================== VOLATILITY INDICATORS ====================

    def bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Dict[str, np.ndarray]:
        """
        Bollinger Bands

        Args:
            period: Period for calculation
            std_dev: Standard deviation multiplier

        Returns:
            Dictionary with upper, middle, and lower bands
        """
        if self.length < period:
            return {
                'upper': np.full(self.length, np.nan),
                'middle': np.full(self.length, np.nan),
                'lower': np.full(self.length, np.nan),
                'bandwidth': np.full(self.length, np.nan),
                'percent_b': np.full(self.length, np.nan)
            }

        middle = self.sma(period)

        # Calculate standard deviation
        std = np.zeros(self.length)
        for i in range(period - 1, self.length):
            window = self.prices[i - period + 1:i + 1]
            std[i] = np.std(window)

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        # Calculate bandwidth
        bandwidth = np.zeros(self.length)
        for i in range(period - 1, self.length):
            if middle[i] != 0:
                bandwidth[i] = (upper[i] - lower[i]) / middle[i]

        # Calculate %B
        percent_b = np.zeros(self.length)
        for i in range(period - 1, self.length):
            if upper[i] != lower[i]:
                percent_b[i] = (self.prices[i] - lower[i]) / (upper[i] - lower[i])

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'bandwidth': bandwidth,
            'percent_b': percent_b
        }

    def atr(self, period: int = 14) -> np.ndarray:
        """
        Average True Range - measures volatility

        Args:
            period: Period for ATR calculation

        Returns:
            Array of ATR values
        """
        if self.length < period + 1:
            return np.full(self.length, np.nan)

        # Calculate True Range (using closing prices as proxy)
        high = self.prices
        low = self.prices * 0.99  # Proxy for low
        close_prev = np.roll(self.prices, 1)

        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - close_prev),
                np.abs(low - close_prev)
            )
        )

        # Calculate ATR using Wilder's smoothing
        atr_values = np.zeros(self.length)
        atr_values[period] = np.mean(tr[:period])

        for i in range(period + 1, self.length):
            atr_values[i] = (atr_values[i - 1] * (period - 1) + tr[i]) / period

        result = np.full(self.length, np.nan)
        result[period:] = atr_values[period:]
        return result

    def keltner_channels(self, period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Dict[str, np.ndarray]:
        """
        Keltner Channels

        Args:
            period: Period for EMA
            atr_period: Period for ATR
            multiplier: ATR multiplier

        Returns:
            Dictionary with upper, middle, and lower channels
        """
        if self.length < max(period, atr_period):
            return {
                'upper': np.full(self.length, np.nan),
                'middle': np.full(self.length, np.nan),
                'lower': np.full(self.length, np.nan)
            }

        middle = self.ema(period)
        atr_values = self.atr(atr_period)

        upper = middle + (atr_values * multiplier)
        lower = middle - (atr_values * multiplier)

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

    def donchian_channels(self, period: int = 20) -> Dict[str, np.ndarray]:
        """
        Donchian Channels

        Args:
            period: Period for channel calculation

        Returns:
            Dictionary with upper, middle, and lower channels
        """
        if self.length < period:
            return {
                'upper': np.full(self.length, np.nan),
                'middle': np.full(self.length, np.nan),
                'lower': np.full(self.length, np.nan)
            }

        upper = np.zeros(self.length)
        lower = np.zeros(self.length)
        middle = np.zeros(self.length)

        for i in range(period - 1, self.length):
            window = self.prices[i - period + 1:i + 1]
            upper[i] = np.max(window)
            lower[i] = np.min(window)
            middle[i] = (upper[i] + lower[i]) / 2

        result_upper = np.full(self.length, np.nan)
        result_lower = np.full(self.length, np.nan)
        result_middle = np.full(self.length, np.nan)

        result_upper[period - 1:] = upper[period - 1:]
        result_lower[period - 1:] = lower[period - 1:]
        result_middle[period - 1:] = middle[period - 1:]

        return {
            'upper': result_upper,
            'middle': result_middle,
            'lower': result_lower
        }

    # ==================== VOLUME INDICATORS ====================

    def obv(self) -> np.ndarray:
        """
        On-Balance Volume

        Returns:
            Array of OBV values
        """
        if self.volumes is None:
            raise ValueError("Volume data required for OBV")

        obv_values = np.zeros(self.length)
        obv_values[0] = self.volumes[0]

        for i in range(1, self.length):
            if self.prices[i] > self.prices[i - 1]:
                obv_values[i] = obv_values[i - 1] + self.volumes[i]
            elif self.prices[i] < self.prices[i - 1]:
                obv_values[i] = obv_values[i - 1] - self.volumes[i]
            else:
                obv_values[i] = obv_values[i - 1]

        return obv_values

    def money_flow_index(self, period: int = 14) -> np.ndarray:
        """
        Money Flow Index

        Args:
            period: Period for MFI calculation

        Returns:
            Array of MFI values (0-100)
        """
        if self.volumes is None:
            raise ValueError("Volume data required for MFI")

        if self.length < period + 1:
            return np.full(self.length, np.nan)

        # Calculate typical price
        tp = self.prices  # Using closing price as proxy

        # Calculate money flow
        money_flow = tp * self.volumes

        # Calculate positive and negative money flow
        positive_mf = np.zeros(self.length)
        negative_mf = np.zeros(self.length)

        for i in range(1, self.length):
            if tp[i] > tp[i - 1]:
                positive_mf[i] = money_flow[i]
            elif tp[i] < tp[i - 1]:
                negative_mf[i] = money_flow[i]

        # Calculate money ratio
        mfi_values = np.zeros(self.length)
        for i in range(period, self.length):
            sum_positive = np.sum(positive_mf[i - period + 1:i + 1])
            sum_negative = np.sum(negative_mf[i - period + 1:i + 1])

            if sum_negative == 0:
                mfi_values[i] = 100
            else:
                money_ratio = sum_positive / sum_negative
                mfi_values[i] = 100 - (100 / (1 + money_ratio))

        result = np.full(self.length, np.nan)
        result[period:] = mfi_values[period:]
        return result

    def volume_sma(self, period: int = 20) -> np.ndarray:
        """
        Volume Simple Moving Average

        Args:
            period: Period for volume SMA

        Returns:
            Array of volume SMA values
        """
        if self.volumes is None:
            raise ValueError("Volume data required for Volume SMA")

        if self.length < period:
            return np.full(self.length, np.nan)

        volume_sma_values = np.convolve(self.volumes, np.ones(period) / period, mode='valid')
        result = np.full(self.length, np.nan)
        result[period - 1:] = volume_sma_values
        return result

    def volume_profile(self, bins: int = 50) -> Dict[str, np.ndarray]:
        """
        Volume Profile - shows volume at different price levels

        Args:
            bins: Number of price bins

        Returns:
            Dictionary with price levels and corresponding volumes
        """
        if self.volumes is None:
            raise ValueError("Volume data required for Volume Profile")

        # Create price bins
        price_min = np.min(self.prices)
        price_max = np.max(self.prices)
        price_bins = np.linspace(price_min, price_max, bins + 1)

        # Calculate volume at each price level
        volume_at_price = np.zeros(bins)
        for i in range(self.length):
            bin_idx = int((self.prices[i] - price_min) / (price_max - price_min) * bins)
            bin_idx = min(bin_idx, bins - 1)
            volume_at_price[bin_idx] += self.volumes[i]

        return {
            'price_levels': price_bins[:-1],
            'volumes': volume_at_price
        }

    # ==================== OSCILLATOR INDICATORS ====================

    def cmo(self, period: int = 14) -> np.ndarray:
        """
        Chande Momentum Oscillator

        Args:
            period: Period for CMO calculation

        Returns:
            Array of CMO values (-100 to 100)
        """
        if self.length < period + 1:
            return np.full(self.length, np.nan)

        # Calculate price changes
        deltas = np.diff(self.prices)

        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate sum of gains and losses
        cmo_values = np.zeros(self.length)
        for i in range(period, self.length):
            sum_gains = np.sum(gains[i - period:i])
            sum_losses = np.sum(losses[i - period:i])

            if sum_gains + sum_losses == 0:
                cmo_values[i] = 0
            else:
                cmo_values[i] = 100 * (sum_gains - sum_losses) / (sum_gains + sum_losses)

        result = np.full(self.length, np.nan)
        result[period:] = cmo_values[period:]
        return result

    def trix(self, period: int = 15) -> np.ndarray:
        """
        TRIX - triple smoothed exponential moving average

        Args:
            period: Period for TRIX calculation

        Returns:
            Array of TRIX values
        """
        if self.length < period * 3:
            return np.full(self.length, np.nan)

        # Triple smoothed EMA
        ema1 = self.ema(period)
        ema2 = self._calculate_ema_from_array(ema1, period)
        ema3 = self._calculate_ema_from_array(ema2, period)

        # Calculate TRIX (percentage change of triple smoothed EMA)
        trix_values = np.zeros(self.length)
        for i in range(1, self.length):
            if ema3[i - 1] != 0 and not np.isnan(ema3[i - 1]):
                trix_values[i] = 100 * (ema3[i] - ema3[i - 1]) / ema3[i - 1]

        result = np.full(self.length, np.nan)
        result[period * 3:] = trix_values[period * 3:]
        return result

    def ultimate_oscillator(self, period1: int = 7, period2: int = 14, period3: int = 28) -> np.ndarray:
        """
        Ultimate Oscillator

        Args:
            period1: First period
            period2: Second period
            period3: Third period

        Returns:
            Array of Ultimate Oscillator values (0-100)
        """
        if self.length < period3:
            return np.full(self.length, np.nan)

        # Calculate buying pressure and true range
        high = self.prices
        low = self.prices * 0.99
        close_prev = np.roll(self.prices, 1)

        buying_pressure = self.prices - np.minimum(low, close_prev)
        true_range = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - close_prev),
                np.abs(low - close_prev)
            )
        )

        # Calculate average for each period
        def calculate_average(bp, tr, period):
            avg = np.zeros(len(bp))
            for i in range(period, len(bp)):
                avg[i] = np.sum(bp[i - period:i]) / np.sum(tr[i - period:i])
            return avg

        avg1 = calculate_average(buying_pressure, true_range, period1)
        avg2 = calculate_average(buying_pressure, true_range, period2)
        avg3 = calculate_average(buying_pressure, true_range, period3)

        # Calculate Ultimate Oscillator
        uo_values = np.zeros(self.length)
        for i in range(period3, self.length):
            uo_values[i] = 100 * (4 * avg1[i] + 2 * avg2[i] + avg3[i]) / 7

        result = np.full(self.length, np.nan)
        result[period3:] = uo_values[period3:]
        return result

    # ==================== COMBINED SIGNALS ====================

    def get_signals(self, indicators: Optional[List[str]] = None) -> Dict[str, IndicatorResult]:
        """
        Get trading signals from multiple indicators

        Args:
            indicators: List of indicator names to calculate

        Returns:
            Dictionary of indicator results with signals
        """
        if indicators is None:
            indicators = ['rsi', 'macd', 'bollinger_bands', 'stochastic', 'adx']

        results = {}

        if 'rsi' in indicators:
            rsi_values = self.rsi()
            signals = []
            for val in rsi_values:
                if np.isnan(val):
                    signals.append('HOLD')
                elif val < 30:
                    signals.append('BUY')
                elif val > 70:
                    signals.append('SELL')
                else:
                    signals.append('HOLD')

            results['rsi'] = IndicatorResult(
                name='RSI',
                values=rsi_values.tolist(),
                signals=signals,
                strength=0.7,
                description='RSI: <30 oversold, >70 overbought'
            )

        if 'macd' in indicators:
            macd_data = self.macd()
            signals = []
            for i in range(len(macd_data['macd'])):
                if np.isnan(macd_data['macd'][i]) or np.isnan(macd_data['signal'][i]):
                    signals.append('HOLD')
                elif macd_data['macd'][i] > macd_data['signal'][i] and macd_data['histogram'][i] > 0:
                    signals.append('BUY')
                elif macd_data['macd'][i] < macd_data['signal'][i] and macd_data['histogram'][i] < 0:
                    signals.append('SELL')
                else:
                    signals.append('HOLD')

            results['macd'] = IndicatorResult(
                name='MACD',
                values=macd_data['macd'].tolist(),
                signals=signals,
                strength=0.8,
                description='MACD: Bullish when MACD > Signal'
            )

        if 'bollinger_bands' in indicators:
            bb_data = self.bollinger_bands()
            signals = []
            for i in range(len(bb_data['percent_b'])):
                if np.isnan(bb_data['percent_b'][i]):
                    signals.append('HOLD')
                elif bb_data['percent_b'][i] > 1:
                    signals.append('SELL')
                elif bb_data['percent_b'][i] < 0:
                    signals.append('BUY')
                else:
                    signals.append('HOLD')

            results['bollinger_bands'] = IndicatorResult(
                name='Bollinger Bands',
                values=bb_data['percent_b'].tolist(),
                signals=signals,
                strength=0.6,
                description='BB: %B > 1 overbought, %B < 0 oversold'
            )

        if 'stochastic' in indicators:
            stoch_data = self.stochastic()
            signals = []
            for i in range(len(stoch_data['k'])):
                if np.isnan(stoch_data['k'][i]) or np.isnan(stoch_data['d'][i]):
                    signals.append('HOLD')
                elif stoch_data['k'][i] < 20 and stoch_data['d'][i] < 20:
                    signals.append('BUY')
                elif stoch_data['k'][i] > 80 and stoch_data['d'][i] > 80:
                    signals.append('SELL')
                else:
                    signals.append('HOLD')

            results['stochastic'] = IndicatorResult(
                name='Stochastic',
                values=stoch_data['k'].tolist(),
                signals=signals,
                strength=0.65,
                description='Stochastic: <20 oversold, >80 overbought'
            )

        if 'adx' in indicators:
            adx_data = self.adx()
            signals = []
            for i in range(len(adx_data['adx'])):
                if np.isnan(adx_data['adx'][i]):
                    signals.append('HOLD')
                elif adx_data['adx'][i] > 25:
                    if adx_data['plus_di'][i] > adx_data['minus_di'][i]:
                        signals.append('BUY')
                    else:
                        signals.append('SELL')
                else:
                    signals.append('HOLD')

            results['adx'] = IndicatorResult(
                name='ADX',
                values=adx_data['adx'].tolist(),
                signals=signals,
                strength=0.75,
                description='ADX: >25 strong trend, +DI > -DI bullish'
            )

        return results

    def get_combined_signal(self, indicators: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Get combined trading signal from all indicators

        Args:
            indicators: List of indicator names to use

        Returns:
            Dictionary with combined signal and confidence
        """
        signals_data = self.get_signals(indicators)

        buy_count = sum(1 for s in signals_data.values() if s.signals[-1] == 'BUY')
        sell_count = sum(1 for s in signals_data.values() if s.signals[-1] == 'SELL')
        hold_count = sum(1 for s in signals_data.values() if s.signals[-1] == 'HOLD')

        total = len(signals_data)
        if total == 0:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'buy_count': 0,
                'sell_count': 0,
                'hold_count': 0
            }

        # Calculate weighted confidence
        buy_weight = sum(s.strength for s in signals_data.values() if s.signals[-1] == 'BUY')
        sell_weight = sum(s.strength for s in signals_data.values() if s.signals[-1] == 'SELL')

        if buy_count > sell_count:
            signal = 'BUY'
            confidence = min(buy_weight / total, 1.0)
        elif sell_count > buy_count:
            signal = 'SELL'
            confidence = min(sell_weight / total, 1.0)
        else:
            signal = 'HOLD'
            confidence = 0.5

        return {
            'signal': signal,
            'confidence': confidence,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'details': {name: {'signal': ind.signals[-1], 'strength': ind.strength}
                       for name, ind in signals_data.items()}
        }


# ==================== HELPER FUNCTIONS ====================

def calculate_all_indicators(prices: List[float], volumes: Optional[List[float]] = None) -> Dict[str, any]:
    """
    Calculate all available indicators for a given price series

    Args:
        prices: List of closing prices
        volumes: Optional list of volume values

    Returns:
        Dictionary with all indicator values
    """
    indicators = TechnicalIndicators(prices, volumes)

    results = {
        'trend': {
            'sma_20': indicators.sma(20).tolist(),
            'sma_50': indicators.sma(50).tolist(),
            'ema_20': indicators.ema(20).tolist(),
            'ema_50': indicators.ema(50).tolist(),
            'macd': indicators.macd(),
            'adx': indicators.adx()
        },
        'momentum': {
            'rsi': indicators.rsi().tolist(),
            'stochastic': indicators.stochastic(),
            'williams_r': indicators.williams_r().tolist(),
            'momentum': indicators.momentum().tolist(),
            'roc': indicators.roc().tolist(),
            'cci': indicators.cci().tolist()
        },
        'volatility': {
            'bollinger_bands': indicators.bollinger_bands(),
            'atr': indicators.atr().tolist(),
            'keltner_channels': indicators.keltner_channels(),
            'donchian_channels': indicators.donchian_channels()
        },
        'oscillator': {
            'cmo': indicators.cmo().tolist(),
            'trix': indicators.trix().tolist(),
            'ultimate_oscillator': indicators.ultimate_oscillator().tolist()
        }
    }

    if volumes is not None:
        results['volume'] = {
            'obv': indicators.obv().tolist(),
            'mfi': indicators.money_flow_index().tolist(),
            'volume_sma': indicators.volume_sma().tolist()
        }

    return results


def get_trading_signals(prices: List[float], volumes: Optional[List[float]] = None) -> Dict[str, any]:
    """
    Get comprehensive trading signals for a stock

    Args:
        prices: List of closing prices
        volumes: Optional list of volume values

    Returns:
        Dictionary with all signals and recommendations
    """
    indicators = TechnicalIndicators(prices, volumes)

    return {
        'individual_signals': indicators.get_signals(),
        'combined_signal': indicators.get_combined_signal(),
        'current_price': prices[-1] if prices else None,
        'price_change': (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) > 1 else 0
    }
