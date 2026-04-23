"""
Market Data Module
Handles market data fetching, quotes, and historical data
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd

from .error_handler import (
    MarketDataError, AuthenticationError, ValidationError,
    retry_on_failure, with_error_handling, RateLimiter
)
from .logging_config import get_logger
from .client import BrokerClient

logger = get_logger('pyportman.market')


# Data classes
@dataclass
class Quote:
    """Market quote data class"""
    symbol: str
    last_price: float
    change: float
    change_percent: float
    volume: int
    open: float
    high: float
    low: float
    close: float
    bid_price: float = 0.0
    ask_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    exchange: str = "NSE"

    @property
    def day_high_low_percent(self) -> float:
        """Day high-low percentage"""
        if self.low > 0:
            return ((self.high - self.low) / self.low) * 100
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert quote to dictionary"""
        return {
            'symbol': self.symbol,
            'last_price': self.last_price,
            'change': self.change,
            'change_percent': self.change_percent,
            'volume': self.volume,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'bid_price': self.bid_price,
            'ask_price': self.ask_price,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange,
            'day_high_low_percent': self.day_high_low_percent
        }


@dataclass
class OHLCV:
    """OHLCV candle data class"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    symbol: str = ""

    @property
    def range(self) -> float:
        """High-Low range"""
        return self.high - self.low

    @property
    def body(self) -> float:
        """Candle body (close - open)"""
        return abs(self.close - self.open)

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish"""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish"""
        return self.close < self.open

    def to_dict(self) -> Dict[str, Any]:
        """Convert OHLCV to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'symbol': self.symbol,
            'range': self.range,
            'body': self.body,
            'is_bullish': self.is_bullish,
            'is_bearish': self.is_bearish
        }


# Market Data Manager
class MarketDataManager:
    """
    Manages market data for a broker client
    """

    def __init__(self, client: BrokerClient):
        """
        Initialize market data manager

        Args:
            client: Broker client instance
        """
        self.client = client
        self.rate_limiter = RateLimiter(max_calls=50, period=60)

        # Instrument token cache
        self._instrument_tokens: Dict[str, str] = {}

    @retry_on_failure(max_retries=3, exceptions=(Exception,))
    @with_error_handling(logger=logger, raise_on_error=True)
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        """
        Get real-time quote for a symbol

        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, MCX, NFO)

        Returns:
            Quote object

        Raises:
            MarketDataError: If fetching quote fails
        """
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            self.rate_limiter.wait_if_needed(logger=logger)

            if self.client.broker == 'zerodha':
                return self._get_quote_zerodha(symbol, exchange)
            elif self.client.broker == 'angel':
                return self._get_quote_angel(symbol, exchange)
            else:
                raise MarketDataError(f"Get quote not implemented for broker: {self.client.broker}")

        except Exception as e:
            raise MarketDataError(f"Failed to get quote for {symbol}: {str(e)}")

    def _get_quote_zerodha(self, symbol: str, exchange: str) -> Quote:
        """Get quote from Zerodha"""
        try:
            instrument_token = self._get_zerodha_instrument_token(symbol, exchange)
            quote_data = self.client.api.quote([instrument_token])

            if not quote_data or instrument_token not in quote_data:
                raise MarketDataError(f"No quote data for {symbol}")

            data = quote_data[instrument_token]

            return Quote(
                symbol=symbol,
                last_price=float(data.get('last_price', 0)),
                change=float(data.get('change', 0)),
                change_percent=float(data.get('net_change', 0)),
                volume=int(data.get('volume', 0)),
                open=float(data.get('ohlc', {}).get('open', 0)),
                high=float(data.get('ohlc', {}).get('high', 0)),
                low=float(data.get('ohlc', {}).get('low', 0)),
                close=float(data.get('ohlc', {}).get('close', 0)),
                bid_price=float(data.get('depth', {}).get('buy', [{}])[0].get('price', 0)),
                ask_price=float(data.get('depth', {}).get('sell', [{}])[0].get('price', 0)),
                exchange=exchange
            )

        except Exception as e:
            raise MarketDataError(f"Zerodha quote error: {str(e)}")

    def _get_quote_angel(self, symbol: str, exchange: str) -> Quote:
        """Get quote from Angel"""
        try:
            instrument_token = self._get_angel_instrument_token(symbol, exchange)

            quote_params = {
                'exchange': exchange,
                'symboltoken': instrument_token,
                'interval': '1'
            }

            quote_data = self.client.api.getLTP(quote_params)

            if not quote_data or 'data' not in quote_data:
                raise MarketDataError(f"No quote data for {symbol}")

            data = quote_data['data']

            return Quote(
                symbol=symbol,
                last_price=float(data.get('ltp', 0)),
                change=0.0,  # Angel doesn't provide change in LTP
                change_percent=0.0,
                volume=int(data.get('totalbuyqty', 0) + data.get('totalsellqty', 0)),
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                exchange=exchange
            )

        except Exception as e:
            raise MarketDataError(f"Angel quote error: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_quotes(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, Quote]:
        """
        Get quotes for multiple symbols

        Args:
            symbols: List of trading symbols
            exchange: Exchange (NSE, BSE, MCX, NFO)

        Returns:
            Dictionary of symbol -> Quote

        Raises:
            MarketDataError: If fetching quotes fails
        """
        quotes = {}

        for symbol in symbols:
            try:
                quote = self.get_quote(symbol, exchange)
                quotes[symbol] = quote
            except Exception as e:
                logger.error(f"Failed to get quote for {symbol}: {e}")

        return quotes

    @retry_on_failure(max_retries=3, exceptions=(Exception,))
    @with_error_handling(logger=logger, raise_on_error=True)
    def get_historical_data(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        interval: str = "day",
        exchange: str = "NSE"
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data

        Args:
            symbol: Trading symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: Interval (minute, day, week, month)
            exchange: Exchange (NSE, BSE, MCX, NFO)

        Returns:
            DataFrame with OHLCV data

        Raises:
            MarketDataError: If fetching historical data fails
        """
        if not self.client.is_authenticated():
            raise AuthenticationError("Client not authenticated")

        try:
            # Parse dates
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')

            self.rate_limiter.wait_if_needed(logger=logger)

            if self.client.broker == 'zerodha':
                return self._get_historical_data_zerodha(symbol, from_dt, to_dt, interval, exchange)
            elif self.client.broker == 'angel':
                return self._get_historical_data_angel(symbol, from_dt, to_dt, interval, exchange)
            else:
                raise MarketDataError(f"Historical data not implemented for broker: {self.client.broker}")

        except Exception as e:
            raise MarketDataError(f"Failed to get historical data for {symbol}: {str(e)}")

    def _get_historical_data_zerodha(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        exchange: str
    ) -> pd.DataFrame:
        """Get historical data from Zerodha"""
        try:
            instrument_token = self._get_zerodha_instrument_token(symbol, exchange)

            data = self.client.api.historical_data(
                instrument_token,
                from_date,
                to_date,
                interval
            )

            df = pd.DataFrame(data)
            df['symbol'] = symbol
            df['exchange'] = exchange

            return df

        except Exception as e:
            raise MarketDataError(f"Zerodha historical data error: {str(e)}")

    def _get_historical_data_angel(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        exchange: str
    ) -> pd.DataFrame:
        """Get historical data from Angel"""
        try:
            instrument_token = self._get_angel_instrument_token(symbol, exchange)

            params = {
                'exchange': exchange,
                'symboltoken': instrument_token,
                'interval': interval,
                'fromdate': from_date.strftime('%Y-%m-%d %H:%M'),
                'todate': to_date.strftime('%Y-%m-%d %H:%M')
            }

            response = self.client.api.getCandleData(params)

            if not response or 'data' not in response:
                raise MarketDataError(f"No historical data for {symbol}")

            df = pd.DataFrame(response['data'])
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['symbol'] = symbol
            df['exchange'] = exchange

            return df

        except Exception as e:
            raise MarketDataError(f"Angel historical data error: {str(e)}")

    @with_error_handling(logger=logger, raise_on_error=True)
    def get_intraday_data(
        self,
        symbol: str,
        interval: str = "minute",
        days: int = 1,
        exchange: str = "NSE"
    ) -> pd.DataFrame:
        """
        Get intraday candle data

        Args:
            symbol: Trading symbol
            interval: Interval (minute, 5minute, 15minute, 30minute, hour)
            days: Number of days of data
            exchange: Exchange (NSE, BSE, MCX, NFO)

        Returns:
            DataFrame with intraday data

        Raises:
            MarketDataError: If fetching intraday data fails
        """
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        return self.get_historical_data(
            symbol,
            from_date.strftime('%Y-%m-%d'),
            to_date.strftime('%Y-%m-%d'),
            interval,
            exchange
        )

    def _get_zerodha_instrument_token(self, symbol: str, exchange: str) -> str:
        """Get instrument token for Zerodha"""
        cache_key = f"{exchange}_{symbol}"

        if cache_key in self._instrument_tokens:
            return self._instrument_tokens[cache_key]

        try:
            instruments = self.client.api.instruments(exchange)

            for inst in instruments:
                if inst.get('tradingsymbol') == symbol:
                    token = inst.get('instrument_token')
                    self._instrument_tokens[cache_key] = token
                    return token

        except Exception as e:
            logger.error(f"Error getting Zerodha instrument token: {e}")

        raise MarketDataError(f"Could not find instrument token for {symbol}")

    def _get_angel_instrument_token(self, symbol: str, exchange: str) -> str:
        """Get instrument token for Angel"""
        cache_key = f"{exchange}_{symbol}"

        if cache_key in self._instrument_tokens:
            return self._instrument_tokens[cache_key]

        try:
            search_params = {
                'exchange': exchange,
                'searchtext': symbol
            }
            result = self.client.api.searchscrip(search_params)

            if result and 'data' in result and len(result['data']) > 0:
                token = result['data'][0].get('symboltoken')
                self._instrument_tokens[cache_key] = token
                return token

        except Exception as e:
            logger.error(f"Error getting Angel instrument token: {e}")

        raise MarketDataError(f"Could not find instrument token for {symbol}")


# Market Data Utilities
class MarketDataUtils:
    """Utility functions for market data analysis"""

    @staticmethod
    def calculate_returns(prices: pd.Series, periods: int = 1) -> pd.Series:
        """
        Calculate returns for a price series

        Args:
            prices: Series of prices
            periods: Number of periods for return calculation

        Returns:
            Series of returns
        """
        return prices.pct_change(periods)

    @staticmethod
    def calculate_volatility(prices: pd.Series, window: int = 20) -> pd.Series:
        """
        Calculate rolling volatility

        Args:
            prices: Series of prices
            window: Rolling window size

        Returns:
            Series of volatility values
        """
        returns = MarketDataUtils.calculate_returns(prices)
        return returns.rolling(window=window).std()

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index

        Args:
            prices: Series of prices
            period: RSI period

        Returns:
            Series of RSI values
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average

        Args:
            prices: Series of prices
            period: SMA period

        Returns:
            Series of SMA values
        """
        return prices.rolling(window=period).mean()

    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average

        Args:
            prices: Series of prices
            period: EMA period

        Returns:
            Series of EMA values
        """
        return prices.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands

        Args:
            prices: Series of prices
            period: Period for calculation
            std_dev: Standard deviation multiplier

        Returns:
            Dictionary with upper, middle, and lower bands
        """
        sma = MarketDataUtils.calculate_sma(prices, period)
        std = prices.rolling(window=period).std()

        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }

    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            prices: Series of prices
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period

        Returns:
            Dictionary with macd, signal, and histogram
        """
        ema_fast = MarketDataUtils.calculate_ema(prices, fast)
        ema_slow = MarketDataUtils.calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = MarketDataUtils.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def detect_support_resistance(
        prices: pd.Series,
        window: int = 20,
        num_levels: int = 3
    ) -> Dict[str, List[float]]:
        """
        Detect support and resistance levels

        Args:
            prices: Series of prices
            window: Window for local extrema detection
            num_levels: Number of levels to return

        Returns:
            Dictionary with support and resistance levels
        """
        # Find local minima (support) and maxima (resistance)
        local_min = prices.rolling(window=window, center=True).min()
        local_max = prices.rolling(window=window, center=True).max()

        # Get unique levels
        support_levels = local_min[local_min == prices].dropna().unique()
        resistance_levels = local_max[local_max == prices].dropna().unique()

        # Sort and get top levels
        support_levels = sorted(support_levels)[-num_levels:]
        resistance_levels = sorted(resistance_levels)[:num_levels]

        return {
            'support': support_levels.tolist(),
            'resistance': resistance_levels.tolist()
        }

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range

        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of close prices
            period: ATR period

        Returns:
            Series of ATR values
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
