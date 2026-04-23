"""
Market Data Integration Module
NSE/BSE live data feeds, option chain, F&O data, corporate actions
"""

import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import time
from dataclasses import dataclass


@dataclass
class MarketQuote:
    """Market quote data structure"""
    symbol: str
    last_price: float
    change: float
    change_percent: float
    volume: int
    open: float
    high: float
    low: float
    close: float
    bid_price: float
    ask_price: float
    timestamp: datetime


@dataclass
class OptionData:
    """Option chain data structure"""
    symbol: str
    strike: float
    expiry: str
    option_type: str  # CE or PE
    last_price: float
    change: float
    change_percent: float
    volume: int
    open_interest: int
    iv: float  # Implied Volatility
    delta: float
    gamma: float
    theta: float
    vega: float


@dataclass
class FOData:
    """F&O data structure"""
    symbol: str
    expiry: str
    lot_size: int
    tick_size: float
    underlying_price: float
    futures_price: float
    basis: float
    basis_percent: float
    open_interest: int
    volume: int


@dataclass
class CorporateAction:
    """Corporate action data structure"""
    symbol: str
    action_type: str  # DIVIDEND, BONUS, SPLIT, RIGHTS, MERGER
    announcement_date: str
    record_date: str
    ex_date: str
    description: str
    ratio: str
    amount: float


class MarketDataProvider:
    """Base class for market data providers"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.base_url = ""

    def get_quote(self, symbol: str) -> MarketQuote:
        """Get quote for a symbol"""
        raise NotImplementedError

    def get_historical_data(self, symbol: str, interval: str,
                            from_date: str, to_date: str) -> pd.DataFrame:
        """Get historical data"""
        raise NotImplementedError

    def get_option_chain(self, symbol: str, expiry: str) -> List[OptionData]:
        """Get option chain"""
        raise NotImplementedError

    def get_fo_data(self, symbol: str) -> List[FOData]:
        """Get F&O data"""
        raise NotImplementedError

    def get_corporate_actions(self, symbol: Optional[str] = None) -> List[CorporateAction]:
        """Get corporate actions"""
        raise NotImplementedError


class NSEDataProvider(MarketDataProvider):
    """NSE Market Data Provider"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://www.nseindia.com"
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_quote(self, symbol: str) -> MarketQuote:
        """Get quote from NSE"""
        try:
            url = f"{self.base_url}/api/quote-equity?symbol={symbol}"
            response = self.session.get(url)
            data = response.json()

            if data.get("status") == "success":
                price_info = data["data"][0]
                meta_info = price_info["meta"]
                price_data = price_info["priceInfo"]

                return MarketQuote(
                    symbol=symbol,
                    last_price=price_data["lastPrice"],
                    change=price_data["change"],
                    change_percent=price_data["pChange"],
                    volume=price_data["totalTradedVolume"],
                    open=price_data["open"],
                    high=price_data["intraDayHigh"],
                    low=price_data["intraDayLow"],
                    close=price_data["previousClose"],
                    bid_price=price_data.get("buyPrice1", 0),
                    ask_price=price_data.get("sellPrice1", 0),
                    timestamp=datetime.now()
                )
        except Exception as e:
            print(f"NSE quote error: {e}")

        return MarketQuote(symbol=symbol, last_price=0, change=0, change_percent=0,
                          volume=0, open=0, high=0, low=0, close=0,
                          bid_price=0, ask_price=0, timestamp=datetime.now())

    def get_historical_data(self, symbol: str, interval: str,
                            from_date: str, to_date: str) -> pd.DataFrame:
        """Get historical data from NSE"""
        try:
            url = f"{self.base_url}/api/historical-cm/equitySymbol"
            params = {
                "symbol": symbol,
                "series": "EQ",
                "from": from_date,
                "to": to_date,
                "interval": interval
            }
            response = self.session.get(url, params=params)
            data = response.json()

            if data.get("status") == "success":
                records = data["data"]
                df = pd.DataFrame(records)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
        except Exception as e:
            print(f"NSE historical data error: {e}")

        return pd.DataFrame()

    def get_option_chain(self, symbol: str, expiry: str) -> List[OptionData]:
        """Get option chain from NSE"""
        try:
            url = f"{self.base_url}/api/option-chain-equities?symbol={symbol}"
            response = self.session.get(url)
            data = response.json()

            options = []
            if data.get("status") == "success":
                for record in data["data"]:
                    ce_data = record.get("CE", {})
                    pe_data = record.get("PE", {})

                    if ce_data:
                        options.append(OptionData(
                            symbol=symbol,
                            strike=record["strikePrice"],
                            expiry=record["expiryDate"],
                            option_type="CE",
                            last_price=ce_data.get("lastPrice", 0),
                            change=ce_data.get("change", 0),
                            change_percent=ce_data.get("pChange", 0),
                            volume=ce_data.get("totalTradedVolume", 0),
                            open_interest=ce_data.get("openInterest", 0),
                            iv=ce_data.get("impliedVolatility", 0),
                            delta=0, gamma=0, theta=0, vega=0
                        ))

                    if pe_data:
                        options.append(OptionData(
                            symbol=symbol,
                            strike=record["strikePrice"],
                            expiry=record["expiryDate"],
                            option_type="PE",
                            last_price=pe_data.get("lastPrice", 0),
                            change=pe_data.get("change", 0),
                            change_percent=pe_data.get("pChange", 0),
                            volume=pe_data.get("totalTradedVolume", 0),
                            open_interest=pe_data.get("openInterest", 0),
                            iv=pe_data.get("impliedVolatility", 0),
                            delta=0, gamma=0, theta=0, vega=0
                        ))

            return options
        except Exception as e:
            print(f"NSE option chain error: {e}")
            return []

    def get_fo_data(self, symbol: str) -> List[FOData]:
        """Get F&O data from NSE"""
        try:
            url = f"{self.base_url}/api/equity-stockIndices?index=NIFTY%2050"
            response = self.session.get(url)
            data = response.json()

            fo_data = []
            if data.get("status") == "success":
                for record in data["data"]:
                    if record.get("symbol") == symbol:
                        fo_data.append(FOData(
                            symbol=symbol,
                            expiry="",
                            lot_size=record.get("lotSize", 0),
                            tick_size=0.05,
                            underlying_price=record.get("lastPrice", 0),
                            futures_price=0,
                            basis=0,
                            basis_percent=0,
                            open_interest=0,
                            volume=0
                        ))

            return fo_data
        except Exception as e:
            print(f"NSE F&O data error: {e}")
            return []

    def get_corporate_actions(self, symbol: Optional[str] = None) -> List[CorporateAction]:
        """Get corporate actions from NSE"""
        try:
            url = f"{self.base_url}/api/corporates-corporateActions"
            if symbol:
                url += f"?symbol={symbol}"

            response = self.session.get(url)
            data = response.json()

            actions = []
            if data.get("status") == "success":
                for record in data["data"]:
                    actions.append(CorporateAction(
                        symbol=record.get("symbol", ""),
                        action_type=record.get("action", ""),
                        announcement_date=record.get("announcementDate", ""),
                        record_date=record.get("recordDate", ""),
                        ex_date=record.get("exDate", ""),
                        description=record.get("desc", ""),
                        ratio=record.get("ratio", ""),
                        amount=record.get("amount", 0)
                    ))

            return actions
        except Exception as e:
            print(f"NSE corporate actions error: {e}")
            return []


class BSEDataProvider(MarketDataProvider):
    """BSE Market Data Provider"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://api.bseindia.com/BseIndiaAPI"

    def get_quote(self, symbol: str) -> MarketQuote:
        """Get quote from BSE"""
        try:
            url = f"{self.base_url}/api/StockReachGraph/w"
            params = {
                "scripcode": symbol,
                "flag": "0"
            }
            response = self.session.get(url, params=params)
            data = response.json()

            if data:
                return MarketQuote(
                    symbol=symbol,
                    last_price=data.get("dprice_cur", 0),
                    change=data.get("dprice_change", 0),
                    change_percent=data.get("dprice_percent", 0),
                    volume=data.get("volume", 0),
                    open=data.get("open", 0),
                    high=data.get("high", 0),
                    low=data.get("low", 0),
                    close=data.get("close", 0),
                    bid_price=data.get("bid", 0),
                    ask_price=data.get("ask", 0),
                    timestamp=datetime.now()
                )
        except Exception as e:
            print(f"BSE quote error: {e}")

        return MarketQuote(symbol=symbol, last_price=0, change=0, change_percent=0,
                          volume=0, open=0, high=0, low=0, close=0,
                          bid_price=0, ask_price=0, timestamp=datetime.now())

    def get_historical_data(self, symbol: str, interval: str,
                            from_date: str, to_date: str) -> pd.DataFrame:
        """Get historical data from BSE"""
        try:
            url = f"{self.base_url}/api/StockReachGraph/w"
            params = {
                "scripcode": symbol,
                "fromdate": from_date,
                "todate": to_date,
                "flag": "1"
            }
            response = self.session.get(url, params=params)
            data = response.json()

            if data and isinstance(data, list):
                df = pd.DataFrame(data)
                df["timestamp"] = pd.to_datetime(df["date"])
                return df
        except Exception as e:
            print(f"BSE historical data error: {e}")

        return pd.DataFrame()

    def get_option_chain(self, symbol: str, expiry: str) -> List[OptionData]:
        """Get option chain from BSE"""
        # BSE option chain implementation
        return []

    def get_fo_data(self, symbol: str) -> List[FOData]:
        """Get F&O data from BSE"""
        try:
            url = f"{self.base_url}/api/Derivates/w"
            params = {"scripcode": symbol}
            response = self.session.get(url, params=params)
            data = response.json()

            fo_data = []
            if data:
                fo_data.append(FOData(
                    symbol=symbol,
                    expiry=data.get("expiry", ""),
                    lot_size=data.get("lotsize", 0),
                    tick_size=0.05,
                    underlying_price=data.get("underlying", 0),
                    futures_price=data.get("futures", 0),
                    basis=0,
                    basis_percent=0,
                    open_interest=data.get("oi", 0),
                    volume=data.get("volume", 0)
                ))

            return fo_data
        except Exception as e:
            print(f"BSE F&O data error: {e}")
            return []

    def get_corporate_actions(self, symbol: Optional[str] = None) -> List[CorporateAction]:
        """Get corporate actions from BSE"""
        try:
            url = f"{self.base_url}/api/CorporateAnnouncements/w"
            if symbol:
                url += f"?scripcode={symbol}"

            response = self.session.get(url)
            data = response.json()

            actions = []
            if data and isinstance(data, list):
                for record in data:
                    actions.append(CorporateAction(
                        symbol=record.get("scripcode", ""),
                        action_type=record.get("category", ""),
                        announcement_date=record.get("ann_dt", ""),
                        record_date=record.get("rec_dt", ""),
                        ex_date=record.get("ex_dt", ""),
                        description=record.get("desc", ""),
                        ratio=record.get("ratio", ""),
                        amount=record.get("amount", 0)
                    ))

            return actions
        except Exception as e:
            print(f"BSE corporate actions error: {e}")
            return []


class MarketDataManager:
    """Unified market data manager"""

    def __init__(self):
        self.providers = {
            "NSE": NSEDataProvider(),
            "BSE": BSEDataProvider()
        }
        self.cache = {}
        self.cache_expiry = {}

    def add_provider(self, name: str, provider: MarketDataProvider):
        """Add a market data provider"""
        self.providers[name] = provider

    def get_quote(self, symbol: str, exchange: str = "NSE") -> MarketQuote:
        """Get quote from specified exchange"""
        provider = self.providers.get(exchange)
        if provider:
            return provider.get_quote(symbol)
        return MarketQuote(symbol=symbol, last_price=0, change=0, change_percent=0,
                          volume=0, open=0, high=0, low=0, close=0,
                          bid_price=0, ask_price=0, timestamp=datetime.now())

    def get_multiple_quotes(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, MarketQuote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        for symbol in symbols:
            quotes[symbol] = self.get_quote(symbol, exchange)
        return quotes

    def get_historical_data(self, symbol: str, interval: str = "day",
                            from_date: Optional[str] = None,
                            to_date: Optional[str] = None,
                            exchange: str = "NSE") -> pd.DataFrame:
        """Get historical data"""
        if not from_date:
            from_date = (datetime.now() - timedelta(days=365)).strftime("%d-%m-%Y")
        if not to_date:
            to_date = datetime.now().strftime("%d-%m-%Y")

        provider = self.providers.get(exchange)
        if provider:
            return provider.get_historical_data(symbol, interval, from_date, to_date)
        return pd.DataFrame()

    def get_option_chain(self, symbol: str, expiry: Optional[str] = None,
                        exchange: str = "NSE") -> pd.DataFrame:
        """Get option chain as DataFrame"""
        provider = self.providers.get(exchange)
        if provider:
            options = provider.get_option_chain(symbol, expiry or "")
            return pd.DataFrame([vars(opt) for opt in options])
        return pd.DataFrame()

    def get_fo_data(self, symbol: str, exchange: str = "NSE") -> pd.DataFrame:
        """Get F&O data as DataFrame"""
        provider = self.providers.get(exchange)
        if provider:
            fo_list = provider.get_fo_data(symbol)
            return pd.DataFrame([vars(fo) for fo in fo_list])
        return pd.DataFrame()

    def get_corporate_actions(self, symbol: Optional[str] = None,
                             exchange: str = "NSE") -> pd.DataFrame:
        """Get corporate actions as DataFrame"""
        provider = self.providers.get(exchange)
        if provider:
            actions = provider.get_corporate_actions(symbol)
            return pd.DataFrame([vars(action) for action in actions])
        return pd.DataFrame()

    def get_market_movers(self, exchange: str = "NSE", top_n: int = 10) -> Dict[str, pd.DataFrame]:
        """Get top gainers and losers"""
        try:
            url = f"https://www.nseindia.com/api/marketStatus-preOpen"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            data = response.json()

            gainers = []
            losers = []

            if data.get("status") == "success":
                for record in data.get("data", []):
                    if record.get("pChange", 0) > 0:
                        gainers.append(record)
                    else:
                        losers.append(record)

                gainers_df = pd.DataFrame(gainers[:top_n])
                losers_df = pd.DataFrame(losers[:top_n])

                return {
                    "gainers": gainers_df,
                    "losers": losers_df
                }
        except Exception as e:
            print(f"Market movers error: {e}")

        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame()}

    def get_index_data(self, index: str = "NIFTY 50") -> Dict:
        """Get index data"""
        try:
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={index}"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            data = response.json()

            if data.get("status") == "success":
                return data["data"][0] if data["data"] else {}
        except Exception as e:
            print(f"Index data error: {e}")

        return {}

    def get_live_feed(self, symbols: List[str], exchange: str = "NSE",
                     callback=None) -> None:
        """Get live feed for symbols (streaming)"""
        while True:
            quotes = self.get_multiple_quotes(symbols, exchange)
            if callback:
                callback(quotes)
            time.sleep(1)  # Poll every second

    def export_data(self, data: pd.DataFrame, filename: str, format: str = "excel"):
        """Export data to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_filename = f"{filename}_{timestamp}"

        if format == "excel":
            full_filename += ".xlsx"
            data.to_excel(full_filename, index=False)
        elif format == "csv":
            full_filename += ".csv"
            data.to_csv(full_filename, index=False)
        elif format == "json":
            full_filename += ".json"
            data.to_json(full_filename, orient="records", indent=2)

        return full_filename


# Utility functions
def calculate_greeks(option_price: float, underlying_price: float,
                    strike: float, time_to_expiry: float,
                    risk_free_rate: float = 0.06, volatility: float = 0.2) -> Dict:
    """Calculate option Greeks using Black-Scholes model"""
    from scipy.stats import norm
    import math

    d1 = (math.log(underlying_price / strike) +
          (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (volatility * math.sqrt(time_to_expiry))
    d2 = d1 - volatility * math.sqrt(time_to_expiry)

    delta = norm.cdf(d1)
    gamma = norm.pdf(d1) / (underlying_price * volatility * math.sqrt(time_to_expiry))
    theta = (-underlying_price * norm.pdf(d1) * volatility) / (2 * math.sqrt(time_to_expiry))
    vega = underlying_price * norm.pdf(d1) * math.sqrt(time_to_expiry)

    return {
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega
    }


def calculate_pcr(option_chain: pd.DataFrame) -> float:
    """Calculate Put-Call Ratio from option chain"""
    call_oi = option_chain[option_chain["option_type"] == "CE"]["open_interest"].sum()
    put_oi = option_chain[option_chain["option_type"] == "PE"]["open_interest"].sum()

    if call_oi > 0:
        return put_oi / call_oi
    return 0


def calculate_max_pain(option_chain: pd.DataFrame) -> float:
    """Calculate Max Pain strike price"""
    strikes = option_chain["strike"].unique()
    max_pain = 0
    min_pain = float("inf")

    for strike in strikes:
        call_pain = option_chain[(option_chain["strike"] == strike) &
                                 (option_chain["option_type"] == "CE")]
        put_pain = option_chain[(option_chain["strike"] == strike) &
                                (option_chain["option_type"] == "PE")]

        total_pain = 0
        for _, row in call_pain.iterrows():
            total_pain += max(0, strike - row["last_price"]) * row["open_interest"]

        for _, row in put_pain.iterrows():
            total_pain += max(0, row["last_price"] - strike) * row["open_interest"]

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain = strike

    return max_pain
