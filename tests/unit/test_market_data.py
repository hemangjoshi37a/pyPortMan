"""Unit tests for market_data module"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import pandas as pd

from core.market_data import (
    Quote,
    OHLCV,
    MarketDataManager,
    MarketDataUtils
)


class TestQuote:
    """Test Quote dataclass"""

    def test_quote_creation(self):
        """Test creating a Quote"""
        quote = Quote(
            symbol='RELIANCE',
            last_price=2500.0,
            change=50.0,
            change_percent=2.04,
            volume=1000000,
            open=2480.0,
            high=2520.0,
            low=2470.0,
            close=2450.0,
            bid_price=2499.0,
            ask_price=2501.0,
            timestamp=datetime.now(),
            exchange='NSE'
        )

        assert quote.symbol == 'RELIANCE'
        assert quote.last_price == 2500.0
        assert quote.change == 50.0

    def test_quote_to_dict(self):
        """Test converting Quote to dict"""
        quote = Quote(
            symbol='RELIANCE',
            last_price=2500.0,
            change=50.0,
            change_percent=2.04,
            volume=1000000,
            open=2480.0,
            high=2520.0,
            low=2470.0,
            close=2450.0,
            bid_price=2499.0,
            ask_price=2501.0,
            timestamp=datetime.now(),
            exchange='NSE'
        )

        result = quote.to_dict()
        assert isinstance(result, dict)
        assert result['symbol'] == 'RELIANCE'
        assert result['last_price'] == 2500.0

    def test_quote_day_high_low_percent(self):
        """Test day_high_low_percent calculation"""
        quote = Quote(
            symbol='RELIANCE',
            last_price=2500.0,
            change=50.0,
            change_percent=2.04,
            volume=1000000,
            open=2480.0,
            high=2520.0,
            low=2470.0,
            close=2450.0,
            bid_price=2499.0,
            ask_price=2501.0,
            timestamp=datetime.now(),
            exchange='NSE'
        )

        # (high - low) / low * 100
        expected = (2520.0 - 2470.0) / 2470.0 * 100
        assert abs(quote.day_high_low_percent - expected) < 0.01


class TestOHLCV:
    """Test OHLCV dataclass"""

    def test_ohlcv_creation(self):
        """Test creating OHLCV"""
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open=2400.0,
            high=2450.0,
            low=2380.0,
            close=2420.0,
            volume=1000000,
            symbol='RELIANCE'
        )

        assert ohlcv.open == 2400.0
        assert ohlcv.high == 2450.0
        assert ohlcv.low == 2380.0
        assert ohlcv.close == 2420.0

    def test_ohlcv_range(self):
        """Test range calculation"""
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open=2400.0,
            high=2450.0,
            low=2380.0,
            close=2420.0,
            volume=1000000,
            symbol='RELIANCE'
        )

        expected = 2450.0 - 2380.0
        assert ohlcv.range == expected

    def test_ohlcv_body(self):
        """Test body calculation"""
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open=2400.0,
            high=2450.0,
            low=2380.0,
            close=2420.0,
            volume=1000000,
            symbol='RELIANCE'
        )

        expected = abs(2420.0 - 2400.0)
        assert ohlcv.body == expected

    def test_ohlcv_is_bullish(self):
        """Test bullish candle detection"""
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open=2400.0,
            high=2450.0,
            low=2380.0,
            close=2420.0,
            volume=1000000,
            symbol='RELIANCE'
        )

        assert ohlcv.is_bullish is True

    def test_ohlcv_is_bearish(self):
        """Test bearish candle detection"""
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open=2420.0,
            high=2450.0,
            low=2380.0,
            close=2400.0,
            volume=1000000,
            symbol='RELIANCE'
        )

        assert ohlcv.is_bearish is True

    def test_ohlcv_to_dict(self):
        """Test converting OHLCV to dict"""
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open=2400.0,
            high=2450.0,
            low=2380.0,
            close=2420.0,
            volume=1000000,
            symbol='RELIANCE'
        )

        result = ohlcv.to_dict()
        assert isinstance(result, dict)
        assert result['open'] == 2400.0
        assert result['close'] == 2420.0


class TestMarketDataUtils:
    """Test MarketDataUtils class"""

    def test_calculate_returns(self):
        """Test calculating returns"""
        prices = [100, 105, 110, 108, 112]
        returns = MarketDataUtils.calculate_returns(prices)

        assert len(returns) == len(prices) - 1
        assert abs(returns[0] - 0.05) < 0.01  # (105-100)/100

    def test_calculate_volatility(self):
        """Test calculating volatility"""
        prices = [100, 105, 110, 108, 112, 115, 118]
        volatility = MarketDataUtils.calculate_volatility(prices, window=5)

        assert volatility > 0

    def test_calculate_rsi(self):
        """Test calculating RSI"""
        prices = [100, 102, 104, 103, 105, 107, 106, 108, 110, 112]
        rsi = MarketDataUtils.calculate_rsi(prices, period=7)

        assert 0 <= rsi <= 100

    def test_calculate_sma(self):
        """Test calculating SMA"""
        prices = [100, 102, 104, 106, 108]
        sma = MarketDataUtils.calculate_sma(prices, period=3)

        expected = (104 + 106 + 108) / 3
        assert abs(sma - expected) < 0.01

    def test_calculate_ema(self):
        """Test calculating EMA"""
        prices = [100, 102, 104, 106, 108]
        ema = MarketDataUtils.calculate_ema(prices, period=3)

        assert ema > 0

    def test_calculate_bollinger_bands(self):
        """Test calculating Bollinger Bands"""
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        upper, middle, lower = MarketDataUtils.calculate_bollinger_bands(prices, period=5, std_dev=2.0)

        assert upper > middle > lower

    def test_calculate_macd(self):
        """Test calculating MACD"""
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122]
        macd, signal, histogram = MarketDataUtils.calculate_macd(prices)

        assert len(macd) > 0
        assert len(signal) > 0
        assert len(histogram) > 0

    def test_calculate_atr(self):
        """Test calculating ATR"""
        high = [105, 107, 109, 111, 113]
        low = [95, 97, 99, 101, 103]
        close = [100, 102, 104, 106, 108]

        atr = MarketDataUtils.calculate_atr(high, low, close, period=3)

        assert atr > 0

    def test_detect_support_resistance(self):
        """Test detecting support and resistance levels"""
        prices = [100, 105, 110, 108, 112, 115, 110, 105, 100, 95, 100, 105]
        levels = MarketDataUtils.detect_support_resistance(prices, window=5, num_levels=3)

        assert len(levels) > 0
        assert len(levels) <= 3


class TestMarketDataManager:
    """Test MarketDataManager class"""

    @pytest.fixture
    def mock_client(self):
        """Mock broker client"""
        client = Mock()
        client.broker = 'zerodha'
        client.account_name = 'test_account'
        client._authenticated = True
        return client

    @pytest.fixture
    def market_data_manager(self, mock_client):
        """Create MarketDataManager instance"""
        return MarketDataManager(mock_client)

    def test_initialization(self, market_data_manager):
        """Test MarketDataManager initialization"""
        assert market_data_manager.client is not None
        assert market_data_manager._rate_limiter is not None
        assert market_data_manager._instrument_tokens == {}

    def test_get_quote_zerodha(self, market_data_manager):
        """Test getting quote from Zerodha"""
        # Mock the API response
        market_data_manager.client.api = Mock()
        market_data_manager.client.api.quote.return_value = {
            'RELIANCE': {
                'last_price': 2500.0,
                'change': 50.0,
                'change_percent': 2.04,
                'volume': 1000000,
                'ohlc': {'open': 2480.0, 'high': 2520.0, 'low': 2470.0, 'close': 2450.0},
                'depth': {'buy': [{'price': 2499.0}], 'sell': [{'price': 2501.0}]}
            }
        }

        quote = market_data_manager.get_quote('RELIANCE', 'NSE')

        assert quote.symbol == 'RELIANCE'
        assert quote.last_price == 2500.0

    def test_get_quotes_batch(self, market_data_manager):
        """Test getting batch quotes"""
        market_data_manager.client.api = Mock()
        market_data_manager.client.api.quote.return_value = {
            'RELIANCE': {'last_price': 2500.0, 'change': 50.0, 'change_percent': 2.04,
                       'volume': 1000000, 'ohlc': {'open': 2480.0, 'high': 2520.0, 'low': 2470.0, 'close': 2450.0},
                       'depth': {'buy': [{'price': 2499.0}], 'sell': [{'price': 2501.0}]}},
            'TCS': {'last_price': 3500.0, 'change': 70.0, 'change_percent': 2.04,
                   'volume': 500000, 'ohlc': {'open': 3480.0, 'high': 3520.0, 'low': 3470.0, 'close': 3450.0},
                   'depth': {'buy': [{'price': 3499.0}], 'sell': [{'price': 3501.0}]}}
        }

        quotes = market_data_manager.get_quotes(['RELIANCE', 'TCS'], 'NSE')

        assert len(quotes) == 2
        assert quotes[0].symbol == 'RELIANCE'
        assert quotes[1].symbol == 'TCS'

    def test_get_historical_data(self, market_data_manager):
        """Test getting historical data"""
        market_data_manager.client.api = Mock()
        market_data_manager.client.api.historical_data.return_value = [
            {'date': '2024-01-01', 'open': 2400.0, 'high': 2450.0, 'low': 2380.0, 'close': 2420.0, 'volume': 1000000},
            {'date': '2024-01-02', 'open': 2420.0, 'high': 2470.0, 'low': 2400.0, 'close': 2440.0, 'volume': 1100000}
        ]

        df = market_data_manager.get_historical_data(
            'RELIANCE',
            '2024-01-01',
            '2024-01-02',
            'day',
            'NSE'
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'open' in df.columns
        assert 'close' in df.columns

    def test_get_intraday_data(self, market_data_manager):
        """Test getting intraday data"""
        market_data_manager.client.api = Mock()
        market_data_manager.client.api.historical_data.return_value = [
            {'date': '2024-01-01 09:15:00', 'open': 2400.0, 'high': 2410.0, 'low': 2395.0, 'close': 2405.0, 'volume': 100000},
            {'date': '2024-01-01 09:30:00', 'open': 2405.0, 'high': 2415.0, 'low': 2400.0, 'close': 2410.0, 'volume': 120000}
        ]

        df = market_data_manager.get_intraday_data('RELIANCE', '15minute', 1, 'NSE')

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_instrument_token_caching(self, market_data_manager):
        """Test instrument token caching"""
        market_data_manager.client.api = Mock()
        market_data_manager.client.api.instruments.return_value = [
            {'instrument_token': '123456', 'tradingsymbol': 'RELIANCE', 'exchange': 'NSE'}
        ]

        # First call - should fetch from API
        token1 = market_data_manager._get_zerodha_instrument_token('RELIANCE', 'NSE')

        # Second call - should use cache
        token2 = market_data_manager._get_zerodha_instrument_token('RELIANCE', 'NSE')

        assert token1 == token2
        # API should be called only once
        assert market_data_manager.client.api.instruments.call_count == 1
