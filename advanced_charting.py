"""
Advanced Charting Module
Candlestick charts with technical indicators (RSI, MACD, Bollinger Bands)
Multi-stock comparison and custom indicator support
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class TechnicalIndicators:
    """Technical indicators calculation"""

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Bollinger Bands"""
        sma = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            "middle": sma,
            "upper": upper_band,
            "lower": lower_band
        }

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Stochastic Oscillator"""
        low_min = low.rolling(window=k_period).min()
        high_max = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=d_period).mean()

        return {
            "k": k_percent,
            "d": d_percent
        }

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]:
        """Average Directional Index"""
        tr = TechnicalIndicators.atr(high, low, close, period)

        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm), 0)
        minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > plus_dm), 0)
        minus_dm = minus_dm.abs()

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)

        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        adx = dx.rolling(window=period).mean()

        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di
        }

    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R"""
        high_max = high.rolling(window=period).max()
        low_min = low.rolling(window=period).min()
        return -100 * ((high_max - close) / (high_max - low_min))

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        return (tp - sma_tp) / (0.015 * mad)

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        obv = np.where(close > close.shift(), volume,
                      np.where(close < close.shift(), -volume, 0))
        return pd.Series(obv, index=close.index).cumsum()

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Volume Weighted Average Price"""
        tp = (high + low + close) / 3
        return (tp * volume).cumsum() / volume.cumsum()

    @staticmethod
    def pivot_points(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, float]:
        """Pivot Points"""
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)

        return {
            "pivot": pivot.iloc[-1],
            "r1": r1.iloc[-1],
            "r2": r2.iloc[-1],
            "r3": r3.iloc[-1],
            "s1": s1.iloc[-1],
            "s2": s2.iloc[-1],
            "s3": s3.iloc[-1]
        }


class CandlestickChart:
    """Candlestick chart with indicators"""

    def __init__(self, figsize: Tuple[int, int] = (14, 10)):
        self.figsize = figsize
        self.fig = None
        self.axes = None

    def plot_candlestick(self, ax, data: pd.DataFrame, title: str = ""):
        """Plot candlestick chart"""
        data = data.copy()
        data.index = pd.to_datetime(data.index)

        # Calculate width of candle
        width = 0.6
        width2 = 0.1

        # Define colors
        up_color = '#26a69a'
        down_color = '#ef5350'

        # Separate up and down candles
        up = data[data['close'] >= data['open']]
        down = data[data['close'] < data['open']]

        # Plot up candles
        ax.bar(up.index, up['close'] - up['open'], width, bottom=up['open'],
               color=up_color, edgecolor='black')
        ax.bar(up.index, up['high'] - up['close'], width2, bottom=up['close'],
               color=up_color, edgecolor='black')
        ax.bar(up.index, up['low'] - up['open'], width2, bottom=up['open'],
               color=up_color, edgecolor='black')

        # Plot down candles
        ax.bar(down.index, down['close'] - down['open'], width, bottom=down['open'],
               color=down_color, edgecolor='black')
        ax.bar(down.index, down['high'] - down['open'], width2, bottom=down['open'],
               color=down_color, edgecolor='black')
        ax.bar(down.index, down['low'] - down['close'], width2, bottom=down['close'],
               color=down_color, edgecolor='black')

        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    def plot_indicator(self, ax, data: pd.Series, name: str, color: str = 'blue',
                      fill: bool = False, fill_alpha: float = 0.3):
        """Plot indicator line"""
        ax.plot(data.index, data.values, label=name, color=color, linewidth=1.5)

        if fill:
            ax.fill_between(data.index, data.values, alpha=fill_alpha, color=color)

        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    def plot_bollinger_bands(self, ax, data: pd.DataFrame, bb_data: Dict[str, pd.Series]):
        """Plot Bollinger Bands"""
        ax.plot(data.index, bb_data['middle'], label='BB Middle', color='orange', alpha=0.7)
        ax.plot(data.index, bb_data['upper'], label='BB Upper', color='red', alpha=0.7)
        ax.plot(data.index, bb_data['lower'], label='BB Lower', color='green', alpha=0.7)
        ax.fill_between(data.index, bb_data['upper'], bb_data['lower'], alpha=0.1, color='gray')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    def plot_macd(self, ax, macd_data: Dict[str, pd.Series]):
        """Plot MACD"""
        ax.plot(macd_data['macd'].index, macd_data['macd'].values,
                label='MACD', color='blue', linewidth=1.5)
        ax.plot(macd_data['signal'].index, macd_data['signal'].values,
                label='Signal', color='orange', linewidth=1.5)

        # Plot histogram
        colors = ['green' if x >= 0 else 'red' for x in macd_data['histogram']]
        ax.bar(macd_data['histogram'].index, macd_data['histogram'].values,
               color=colors, alpha=0.5, label='Histogram')

        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    def plot_rsi(self, ax, rsi_data: pd.Series):
        """Plot RSI"""
        ax.plot(rsi_data.index, rsi_data.values, label='RSI', color='purple', linewidth=1.5)
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Overbought (70)')
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Oversold (30)')
        ax.axhline(y=50, color='gray', linestyle='-', alpha=0.3)
        ax.set_ylim(0, 100)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    def plot_volume(self, ax, data: pd.DataFrame):
        """Plot volume bars"""
        colors = ['green' if row['close'] >= row['open'] else 'red'
                 for _, row in data.iterrows()]
        ax.bar(data.index, data['volume'], color=colors, alpha=0.6)
        ax.set_ylabel('Volume')
        ax.grid(True, alpha=0.3)

    def create_chart(self, data: pd.DataFrame, indicators: List[str] = None,
                    title: str = "Price Chart", show_volume: bool = True) -> plt.Figure:
        """Create complete chart with indicators"""
        if indicators is None:
            indicators = ['sma_20', 'sma_50', 'rsi', 'macd']

        # Calculate number of subplots
        n_subplots = 1
        if show_volume:
            n_subplots += 1
        if 'rsi' in indicators:
            n_subplots += 1
        if 'macd' in indicators:
            n_subplots += 1

        # Create figure
        self.fig, self.axes = plt.subplots(n_subplots, 1, figsize=self.figsize,
                                          sharex=True, gridspec_kw={'height_ratios': [3] + [1] * (n_subplots - 1)})
        if n_subplots == 1:
            self.axes = [self.axes]

        # Plot candlestick
        self.plot_candlestick(self.axes[0], data, title)

        # Plot moving averages
        if 'sma_20' in indicators:
            sma_20 = TechnicalIndicators.sma(data['close'], 20)
            self.plot_indicator(self.axes[0], sma_20, 'SMA 20', color='orange')

        if 'sma_50' in indicators:
            sma_50 = TechnicalIndicators.sma(data['close'], 50)
            self.plot_indicator(self.axes[0], sma_50, 'SMA 50', color='blue')

        if 'ema_12' in indicators:
            ema_12 = TechnicalIndicators.ema(data['close'], 12)
            self.plot_indicator(self.axes[0], ema_12, 'EMA 12', color='purple')

        if 'ema_26' in indicators:
            ema_26 = TechnicalIndicators.ema(data['close'], 26)
            self.plot_indicator(self.axes[0], ema_26, 'EMA 26', color='cyan')

        # Plot Bollinger Bands
        if 'bollinger' in indicators:
            bb_data = TechnicalIndicators.bollinger_bands(data['close'])
            self.plot_bollinger_bands(self.axes[0], data, bb_data)

        ax_idx = 1

        # Plot volume
        if show_volume:
            self.plot_volume(self.axes[ax_idx], data)
            ax_idx += 1

        # Plot RSI
        if 'rsi' in indicators:
            rsi_data = TechnicalIndicators.rsi(data['close'])
            self.plot_rsi(self.axes[ax_idx], rsi_data)
            ax_idx += 1

        # Plot MACD
        if 'macd' in indicators:
            macd_data = TechnicalIndicators.macd(data['close'])
            self.plot_macd(self.axes[ax_idx], macd_data)
            ax_idx += 1

        plt.tight_layout()
        return self.fig

    def save_chart(self, filename: str, dpi: int = 150):
        """Save chart to file"""
        if self.fig:
            self.fig.savefig(filename, dpi=dpi, bbox_inches='tight')
            plt.close(self.fig)


class MultiStockComparison:
    """Multi-stock comparison charts"""

    def __init__(self, figsize: Tuple[int, int] = (16, 10)):
        self.figsize = figsize

    def compare_stocks(self, stocks_data: Dict[str, pd.DataFrame],
                     normalize: bool = True, indicators: List[str] = None) -> plt.Figure:
        """Compare multiple stocks"""
        if indicators is None:
            indicators = ['sma_20']

        n_stocks = len(stocks_data)
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        fig.suptitle('Multi-Stock Comparison', fontsize=16, fontweight='bold')

        # Price comparison
        ax1 = axes[0, 0]
        for symbol, data in stocks_data.items():
            if normalize:
                normalized = (data['close'] / data['close'].iloc[0]) * 100
                ax1.plot(data.index, normalized, label=symbol, linewidth=2)
            else:
                ax1.plot(data.index, data['close'], label=symbol, linewidth=2)

        ax1.set_title('Price Comparison' + (' (Normalized)' if normalize else ''))
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Volume comparison
        ax2 = axes[0, 1]
        for symbol, data in stocks_data.items():
            ax2.plot(data.index, data['volume'], label=symbol, linewidth=1.5, alpha=0.7)

        ax2.set_title('Volume Comparison')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Returns comparison
        ax3 = axes[1, 0]
        for symbol, data in stocks_data.items():
            returns = data['close'].pct_change() * 100
            ax3.plot(data.index, returns, label=symbol, linewidth=1, alpha=0.7)

        ax3.set_title('Daily Returns (%)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)

        # Volatility comparison
        ax4 = axes[1, 1]
        volatilities = {}
        for symbol, data in stocks_data.items():
            returns = data['close'].pct_change()
            volatility = returns.rolling(window=20).std() * np.sqrt(252) * 100
            volatilities[symbol] = volatility
            ax4.plot(data.index, volatility, label=symbol, linewidth=1.5, alpha=0.7)

        ax4.set_title('20-Day Rolling Volatility (Annualized %)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def correlation_heatmap(self, stocks_data: Dict[str, pd.DataFrame]) -> plt.Figure:
        """Create correlation heatmap"""
        returns_df = pd.DataFrame()

        for symbol, data in stocks_data.items():
            returns_df[symbol] = data['close'].pct_change()

        correlation = returns_df.corr()

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(correlation, cmap='coolwarm', vmin=-1, vmax=1)

        # Set ticks
        ax.set_xticks(np.arange(len(correlation.columns)))
        ax.set_yticks(np.arange(len(correlation.index)))
        ax.set_xticklabels(correlation.columns)
        ax.set_yticklabels(correlation.index)

        # Rotate labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

        # Add colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.set_label('Correlation Coefficient')

        # Add text annotations
        for i in range(len(correlation)):
            for j in range(len(correlation.columns)):
                text = ax.text(j, i, f'{correlation.iloc[i, j]:.2f}',
                             ha='center', va='center', color='black')

        ax.set_title('Stock Correlation Heatmap')
        plt.tight_layout()
        return fig

    def performance_summary(self, stocks_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Generate performance summary"""
        summary = []

        for symbol, data in stocks_data.items():
            returns = data['close'].pct_change()

            summary.append({
                'Symbol': symbol,
                'Start Price': data['close'].iloc[0],
                'End Price': data['close'].iloc[-1],
                'Total Return %': ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100,
                'Avg Daily Return %': returns.mean() * 100,
                'Std Dev %': returns.std() * 100,
                'Max Drawdown %': self._calculate_max_drawdown(data['close']),
                'Sharpe Ratio': self._calculate_sharpe_ratio(returns),
                'Total Volume': data['volume'].sum()
            })

        return pd.DataFrame(summary)

    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Calculate maximum drawdown"""
        cumulative = (1 + prices.pct_change()).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min() * 100

    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.06) -> float:
        """Calculate Sharpe ratio"""
        excess_returns = returns.mean() - risk_free_rate / 252
        return excess_returns / returns.std() * np.sqrt(252)


class CustomIndicator:
    """Custom indicator builder"""

    def __init__(self):
        self.indicators = {}

    def add_indicator(self, name: str, calculation: Callable, params: Dict = None):
        """Add custom indicator"""
        self.indicators[name] = {
            'calculation': calculation,
            'params': params or {}
        }

    def calculate(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate all custom indicators"""
        results = {}
        for name, indicator in self.indicators.items():
            try:
                results[name] = indicator['calculation'](data, **indicator['params'])
            except Exception as e:
                print(f"Error calculating {name}: {e}")
        return results

    def remove_indicator(self, name: str):
        """Remove custom indicator"""
        if name in self.indicators:
            del self.indicators[name]


# Predefined custom indicators
def supertrend(data: pd.DataFrame, period: int = 10, multiplier: float = 3) -> Dict[str, pd.Series]:
    """Supertrend indicator"""
    hl2 = (data['high'] + data['low']) / 2
    atr = TechnicalIndicators.atr(data['high'], data['low'], data['close'], period)

    supertrend = hl2 + (multiplier * atr)
    support = hl2 - (multiplier * atr)

    return {
        'supertrend': supertrend,
        'support': support
    }


def ichimoku_cloud(data: pd.DataFrame) -> Dict[str, pd.Series]:
    """Ichimoku Cloud indicator"""
    high_9 = data['high'].rolling(window=9).max()
    low_9 = data['low'].rolling(window=9).min()
    high_26 = data['high'].rolling(window=26).max()
    low_26 = data['low'].rolling(window=26).min()
    high_52 = data['high'].rolling(window=52).max()
    low_52 = data['low'].rolling(window=52).min()

    tenkan_sen = (high_9 + low_9) / 2
    kijun_sen = (high_26 + low_26) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    senkou_span_b = ((high_52 + low_52) / 2).shift(26)
    chikou_span = data['close'].shift(-26)

    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


def heikin_ashi(data: pd.DataFrame) -> pd.DataFrame:
    """Heikin Ashi candles"""
    ha_close = (data['open'] + data['high'] + data['low'] + data['close']) / 4
    ha_open = (data['open'].shift(1) + data['close'].shift(1)) / 2
    ha_open.iloc[0] = data['open'].iloc[0]
    ha_high = data[['high', 'ha_open', 'ha_close']].max(axis=1)
    ha_low = data[['low', 'ha_open', 'ha_close']].min(axis=1)

    return pd.DataFrame({
        'open': ha_open,
        'high': ha_high,
        'low': ha_low,
        'close': ha_close,
        'volume': data['volume']
    })
