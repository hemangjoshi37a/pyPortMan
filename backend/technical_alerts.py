"""
Technical Alerts Module for pyPortMan
Implements technical indicator alerts (RSI, MACD, Moving Averages, Patterns)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import numpy as np

from models import Account, PriceAlert, AlertHistory, TechnicalAlertRule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TechnicalAlertsManager:
    """Manager for technical indicator alerts"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index (RSI)"""
        if len(prices) < period + 1:
            raise ValueError(f"Need at least {period + 1} prices for RSI calculation")

        prices = np.array(prices)
        deltas = np.diff(prices)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    def calculate_macd(
        self,
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow_period + signal_period:
            raise ValueError(f"Need at least {slow_period + signal_period} prices for MACD calculation")

        prices = np.array(prices)

        def ema(data, period):
            return np.array([np.mean(data[:i+1]) if i < period else
                            (data[i] * (2 / (period + 1)) +
                             ema(data[:i], period)[-1] * (1 - 2 / (period + 1)))
                            for i in range(len(data))])

        fast_ema = ema(prices, fast_period)
        slow_ema = ema(prices, slow_period)

        macd_line = fast_ema - slow_ema
        signal_line = ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return {
            "macd": float(macd_line[-1]),
            "signal": float(signal_line[-1]),
            "histogram": float(histogram[-1])
        }

    def calculate_sma(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average (SMA)"""
        if len(prices) < period:
            raise ValueError(f"Need at least {period} prices for SMA calculation")

        return float(np.mean(prices[-period:]))

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average (EMA)"""
        if len(prices) < period:
            raise ValueError(f"Need at least {period} prices for EMA calculation")

        prices = np.array(prices)
        multiplier = 2 / (period + 1)

        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return float(ema)

    def calculate_bollinger_bands(
        self,
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            raise ValueError(f"Need at least {period} prices for Bollinger Bands calculation")

        prices = np.array(prices[-period:])
        middle = np.mean(prices)
        std = np.std(prices)

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        bandwidth = (upper - lower) / middle if middle > 0 else 0

        return {
            "upper": float(upper),
            "middle": float(middle),
            "lower": float(lower),
            "bandwidth": float(bandwidth)
        }

    def check_rsi_alert(
        self,
        prices: List[float],
        overbought: float = 70.0,
        oversold: float = 30.0
    ) -> Dict[str, Any]:
        """Check RSI alert conditions"""
        try:
            rsi = self.calculate_rsi(prices)

            if rsi >= overbought:
                return {"rsi": rsi, "condition": "overbought", "signal": "sell"}
            elif rsi <= oversold:
                return {"rsi": rsi, "condition": "oversold", "signal": "buy"}
            else:
                return {"rsi": rsi, "condition": "neutral", "signal": "hold"}
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return {"error": str(e)}

    def check_macd_alert(self, prices: List[float]) -> Dict[str, Any]:
        """Check MACD alert conditions"""
        try:
            macd_data = self.calculate_macd(prices)

            crossover = None
            if macd_data["histogram"] > 0 and macd_data["macd"] > macd_data["signal"]:
                crossover = "bullish"
            elif macd_data["histogram"] < 0 and macd_data["macd"] < macd_data["signal"]:
                crossover = "bearish"

            signal = "hold"
            if crossover == "bullish":
                signal = "buy"
            elif crossover == "bearish":
                signal = "sell"

            return {
                "macd": macd_data["macd"],
                "signal_line": macd_data["signal"],
                "histogram": macd_data["histogram"],
                "crossover": crossover,
                "signal": signal
            }
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {"error": str(e)}

    def check_ma_crossover_alert(
        self,
        prices: List[float],
        fast_period: int = 10,
        slow_period: int = 20
    ) -> Dict[str, Any]:
        """Check Moving Average crossover alert"""
        try:
            fast_ma = self.calculate_sma(prices, fast_period)
            slow_ma = self.calculate_sma(prices, slow_period)

            if len(prices) < slow_period + 1:
                return {"fast_ma": fast_ma, "slow_ma": slow_ma, "crossover": None, "signal": "hold"}

            prev_fast_ma = self.calculate_sma(prices[:-1], fast_period)
            prev_slow_ma = self.calculate_sma(prices[:-1], slow_period)

            crossover = None
            if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
                crossover = "bullish"
            elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
                crossover = "bearish"

            signal = "hold"
            if crossover == "bullish":
                signal = "buy"
            elif crossover == "bearish":
                signal = "sell"

            return {"fast_ma": fast_ma, "slow_ma": slow_ma, "crossover": crossover, "signal": signal}
        except Exception as e:
            logger.error(f"Error calculating MA crossover: {e}")
            return {"error": str(e)}

    def check_bollinger_band_alert(
        self,
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, Any]:
        """Check Bollinger Band alert conditions"""
        try:
            bands = self.calculate_bollinger_bands(prices, period, std_dev)
            current_price = prices[-1]

            condition = "neutral"
            signal = "hold"

            if current_price >= bands["upper"]:
                condition = "above_upper"
                signal = "sell"
            elif current_price <= bands["lower"]:
                condition = "below_lower"
                signal = "buy"

            return {
                "upper": bands["upper"],
                "middle": bands["middle"],
                "lower": bands["lower"],
                "current_price": current_price,
                "condition": condition,
                "signal": signal,
                "bandwidth": bands["bandwidth"]
            }
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {"error": str(e)}

    def check_volume_alert(
        self,
        volumes: List[float],
        avg_volume_period: int = 20,
        volume_multiplier: float = 2.0
    ) -> Dict[str, Any]:
        """Check volume spike alert"""
        try:
            if len(volumes) < avg_volume_period:
                raise ValueError(f"Need at least {avg_volume_period} volume values")

            current_volume = volumes[-1]
            avg_volume = np.mean(volumes[-avg_volume_period:])
            ratio = current_volume / avg_volume if avg_volume > 0 else 0

            condition = "normal"
            signal = "hold"

            if ratio >= volume_multiplier:
                condition = "high_volume"
                signal = "strong"
            elif ratio <= (1 / volume_multiplier):
                condition = "low_volume"
                signal = "weak"

            return {
                "current_volume": float(current_volume),
                "avg_volume": float(avg_volume),
                "ratio": float(ratio),
                "condition": condition,
                "signal": signal
            }
        except Exception as e:
            logger.error(f"Error calculating volume alert: {e}")
            return {"error": str(e)}

    def check_all_technical_alerts(
        self,
        prices: List[float],
        volumes: Optional[List[float]] = None,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        ma_fast_period: int = 10,
        ma_slow_period: int = 20,
        bb_period: int = 20,
        bb_std_dev: float = 2.0
    ) -> Dict[str, Any]:
        """Check all technical alerts for a stock"""
        results = {
            "rsi": self.check_rsi_alert(prices, rsi_overbought, rsi_oversold),
            "macd": self.check_macd_alert(prices),
            "ma_crossover": self.check_ma_crossover_alert(prices, ma_fast_period, ma_slow_period),
            "bollinger_bands": self.check_bollinger_band_alert(prices, bb_period, bb_std_dev)
        }

        if volumes:
            results["volume"] = self.check_volume_alert(volumes)

        signals = []
        for key, value in results.items():
            if isinstance(value, dict) and "signal" in value:
                signals.append(value["signal"])

        buy_signals = signals.count("buy")
        sell_signals = signals.count("sell")

        if buy_signals > sell_signals:
            overall_signal = "strong_buy" if buy_signals >= 2 else "buy"
        elif sell_signals > buy_signals:
            overall_signal = "strong_sell" if sell_signals >= 2 else "sell"
        else:
            overall_signal = "hold"

        results["overall_signal"] = overall_signal
        results["buy_signals"] = buy_signals
        results["sell_signals"] = sell_signals

        return results

    def get_technical_summary(
        self,
        account_id: int,
        stock: str,
        prices: List[float],
        volumes: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Get complete technical summary for a stock"""
        alerts = self.check_all_technical_alerts(prices, volumes)

        return {
            "account_id": account_id,
            "stock": stock,
            "current_price": prices[-1] if prices else 0,
            "price_change": (prices[-1] - prices[-2]) if len(prices) >= 2 else 0,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat()
        }

    def check_all_active_technical_alerts(self) -> List[Dict[str, Any]]:
        """
        Check all active technical alert rules and send notifications

        Returns:
            List of triggered alerts
        """
        try:
            # Get all active technical alert rules
            rules = self.db.query(TechnicalAlertRule).filter(
                TechnicalAlertRule.enabled == True
            ).all()

            if not rules:
                return []

            triggered_alerts = []

            for rule in rules:
                # Get stocks to check (specific stock or all holdings)
                if rule.stock:
                    stocks_to_check = [(rule.stock, rule.exchange)]
                else:
                    # Get all holdings for this account or all accounts
                    from models import Holding
                    if rule.account_id:
                        holdings = self.db.query(Holding).filter(
                            Holding.account_id == rule.account_id
                        ).all()
                    else:
                        holdings = self.db.query(Holding).join(Account).filter(
                            Account.is_active == True
                        ).all()
                    stocks_to_check = [(h.stock, h.exchange) for h in holdings]

                for stock, exchange in stocks_to_check:
                    # Get price history for this stock
                    # In production, this would fetch from broker API or database
                    # For now, we'll use a placeholder
                    prices = self._get_price_history(stock, exchange)
                    volumes = self._get_volume_history(stock, exchange)

                    if not prices or len(prices) < 30:
                        continue

                    # Check technical indicators based on rule settings
                    results = {}

                    if rule.rsi_enabled:
                        results["rsi"] = self.check_rsi_alert(
                            prices,
                            rule.rsi_overbought,
                            rule.rsi_oversold
                        )

                    if rule.macd_enabled:
                        results["macd"] = self.check_macd_alert(prices)

                    if rule.ma_crossover_enabled:
                        results["ma_crossover"] = self.check_ma_crossover_alert(
                            prices,
                            rule.ma_fast_period,
                            rule.ma_slow_period
                        )

                    if rule.bb_enabled:
                        results["bollinger_bands"] = self.check_bollinger_band_alert(
                            prices,
                            rule.bb_period,
                            rule.bb_std_dev
                        )

                    if rule.volume_enabled and volumes:
                        results["volume"] = self.check_volume_alert(
                            volumes,
                            rule.volume_avg_period,
                            rule.volume_multiplier
                        )

                    # Check if any alerts were triggered
                    for indicator, result in results.items():
                        if isinstance(result, dict) and result.get("signal") in ["buy", "sell", "strong_buy", "strong_sell"]:
                            triggered_alerts.append({
                                "rule_id": rule.id,
                                "stock": stock,
                                "exchange": exchange,
                                "indicator": indicator,
                                "signal": result["signal"],
                                "details": result
                            })

                            # Send notification
                            self._send_technical_alert_notification(
                                rule, stock, indicator, result
                            )

                            # Update rule stats
                            rule.last_triggered_at = datetime.utcnow()
                            rule.trigger_count += 1

                # Update last checked time
                rule.last_checked_at = datetime.utcnow()

            self.db.commit()
            return triggered_alerts

        except Exception as e:
            logger.error(f"Error checking technical alerts: {e}")
            self.db.rollback()
            return []

    def _get_price_history(self, stock: str, exchange: str, days: int = 30) -> List[float]:
        """
        Get price history for a stock
        In production, this would fetch from broker API or database
        """
        # Placeholder - in production, fetch from KiteConnect or database
        # For now, return empty list
        return []

    def _get_volume_history(self, stock: str, exchange: str, days: int = 30) -> List[float]:
        """
        Get volume history for a stock
        In production, this would fetch from broker API or database
        """
        # Placeholder - in production, fetch from KiteConnect or database
        # For now, return empty list
        return []

    def _send_technical_alert_notification(
        self,
        rule: TechnicalAlertRule,
        stock: str,
        indicator: str,
        result: Dict[str, Any]
    ):
        """Send notification for technical alert"""
        try:
            # Get notification channels
            channels = rule.notification_channels.split(",") if rule.notification_channels else ["telegram"]

            # Format message
            signal = result.get("signal", "hold")
            emoji = "🟢" if "buy" in signal else "🔴" if "sell" in signal else "⚪"

            message = f"""{emoji} <b>TECHNICAL ALERT - {stock}</b>

Indicator: {indicator.upper()}
Signal: {signal.upper()}
Current Price: ₹{result.get('current_price', 0):.2f}

Time: {datetime.now().strftime('%H:%M:%S')}"""

            # Send to each channel
            if "telegram" in channels:
                from telegram_alerts import TelegramAlerts
                telegram = TelegramAlerts(self.db)
                telegram._send_alert(f"TECHNICAL_{indicator.upper()}", message)

            # Add other channels (email, SMS, webhook) as needed

            # Log to alert history
            alert = AlertHistory(
                alert_type=f"TECHNICAL_{indicator.upper()}",
                message=message,
                sent_at=datetime.utcnow(),
                success=True
            )
            self.db.add(alert)

        except Exception as e:
            logger.error(f"Error sending technical alert notification: {e}")

    def create_technical_alert_rule(self, rule_data: Dict[str, Any]) -> TechnicalAlertRule:
        """
        Create a new technical alert rule

        Args:
            rule_data: Dictionary with rule parameters

        Returns:
            Created TechnicalAlertRule
        """
        rule = TechnicalAlertRule(
            account_id=rule_data.get("account_id"),
            stock=rule_data.get("stock"),
            exchange=rule_data.get("exchange", "NSE"),
            enabled=rule_data.get("enabled", True),
            rsi_enabled=rule_data.get("rsi_enabled", False),
            rsi_overbought=rule_data.get("rsi_overbought", 70.0),
            rsi_oversold=rule_data.get("rsi_oversold", 30.0),
            rsi_period=rule_data.get("rsi_period", 14),
            macd_enabled=rule_data.get("macd_enabled", False),
            macd_fast_period=rule_data.get("macd_fast_period", 12),
            macd_slow_period=rule_data.get("macd_slow_period", 26),
            macd_signal_period=rule_data.get("macd_signal_period", 9),
            ma_crossover_enabled=rule_data.get("ma_crossover_enabled", False),
            ma_fast_period=rule_data.get("ma_fast_period", 10),
            ma_slow_period=rule_data.get("ma_slow_period", 20),
            bb_enabled=rule_data.get("bb_enabled", False),
            bb_period=rule_data.get("bb_period", 20),
            bb_std_dev=rule_data.get("bb_std_dev", 2.0),
            volume_enabled=rule_data.get("volume_enabled", False),
            volume_avg_period=rule_data.get("volume_avg_period", 20),
            volume_multiplier=rule_data.get("volume_multiplier", 2.0),
            notification_channels=rule_data.get("notification_channels", "telegram")
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        return rule

    def get_technical_alert_rules(self, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all technical alert rules

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            List of technical alert rules
        """
        query = self.db.query(TechnicalAlertRule)

        if account_id:
            query = query.filter(TechnicalAlertRule.account_id == account_id)

        rules = query.all()

        return [
            {
                "id": rule.id,
                "account_id": rule.account_id,
                "stock": rule.stock,
                "exchange": rule.exchange,
                "enabled": rule.enabled,
                "rsi_enabled": rule.rsi_enabled,
                "rsi_overbought": rule.rsi_overbought,
                "rsi_oversold": rule.rsi_oversold,
                "rsi_period": rule.rsi_period,
                "macd_enabled": rule.macd_enabled,
                "ma_crossover_enabled": rule.ma_crossover_enabled,
                "bb_enabled": rule.bb_enabled,
                "volume_enabled": rule.volume_enabled,
                "notification_channels": rule.notification_channels,
                "last_checked_at": rule.last_checked_at.isoformat() if rule.last_checked_at else None,
                "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
                "trigger_count": rule.trigger_count,
                "created_at": rule.created_at.isoformat()
            }
            for rule in rules
        ]

    def delete_technical_alert_rule(self, rule_id: int) -> bool:
        """
        Delete a technical alert rule

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            rule = self.db.query(TechnicalAlertRule).filter(
                TechnicalAlertRule.id == rule_id
            ).first()

            if rule:
                self.db.delete(rule)
                self.db.commit()
                return True

            return False
        except Exception as e:
            logger.error(f"Error deleting technical alert rule: {e}")
            self.db.rollback()
            return False
