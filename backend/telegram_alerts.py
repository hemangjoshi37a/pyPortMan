"""
Telegram Alert System for pyPortMan
Sends notifications for important portfolio events via Telegram Bot

Setup Instructions:
1. Open Telegram, search @BotFather
2. Send /newbot, give it a name
3. Copy the bot token
4. Send /start to your bot
5. Get chat_id: https://api.telegram.org/bot{TOKEN}/getUpdates
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

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


class TelegramAlerts:
    """Manager for Telegram notifications"""

    def __init__(self, db: Session):
        self.db = db
        self._bot = None
        self._config = None

    def _get_config(self) -> Optional[Dict[str, Any]]:
        """Get Telegram configuration from database"""
        try:
            from models import AlertConfig
            config = self.db.query(AlertConfig).first()
            if config:
                return {
                    "bot_token": config.bot_token,
                    "chat_id": config.chat_id,
                    "gtt_alerts_enabled": config.gtt_alerts_enabled,
                    "loss_alerts_enabled": config.loss_alerts_enabled,
                    "daily_summary_enabled": config.daily_summary_enabled,
                    "order_alerts_enabled": config.order_alerts_enabled,
                    "loss_threshold_pct": config.loss_threshold_pct or 5.0
                }
        except Exception as e:
            logger.error(f"Error getting Telegram config: {e}")
        return None

    def _get_bot(self) -> Optional[Bot]:
        """Get or create Telegram Bot instance"""
        if not TELEGRAM_AVAILABLE:
            logger.warning("python-telegram-bot not installed")
            return None

        if self._bot:
            return self._bot

        config = self._get_config()
        if not config or not config.get("bot_token"):
            return None

        try:
            self._bot = Bot(token=config["bot_token"])
            return self._bot
        except Exception as e:
            logger.error(f"Error creating Telegram bot: {e}")
            return None

    def _log_alert(self, alert_type: str, message: str, success: bool):
        """Log alert to AlertHistory"""
        try:
            from models import AlertHistory
            alert = AlertHistory(
                alert_type=alert_type,
                message=message,
                sent_at=datetime.utcnow(),
                success=success
            )
            self.db.add(alert)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging alert history: {e}")

    def send_message(self, chat_id: str, text: str) -> bool:
        """
        Send any message to Telegram

        Args:
            chat_id: Telegram chat ID
            text: Message text

        Returns:
            True if successful, False otherwise
        """
        bot = self._get_bot()
        if not bot:
            logger.warning("Telegram bot not configured")
            return False

        try:
            bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def _send_alert(self, alert_type: str, message: str) -> bool:
        """
        Internal method to send alert with logging

        Args:
            alert_type: Type of alert (GTT_TRIGGERED, BIG_LOSS, etc.)
            message: Formatted message

        Returns:
            True if successful, False otherwise
        """
        config = self._get_config()
        if not config or not config.get("chat_id"):
            logger.warning("Telegram not configured")
            self._log_alert(alert_type, message, False)
            return False

        success = self.send_message(config["chat_id"], message)
        self._log_alert(alert_type, message, success)
        return success

    def send_gtt_triggered_alert(
        self,
        account_id: int,
        account_name: str,
        stock: str,
        trigger_type: str,
        price: float,
        pnl: float
    ) -> bool:
        """
        Send alert when GTT is triggered

        Args:
            account_id: Account ID
            account_name: Account name
            stock: Stock symbol
            trigger_type: TARGET_HIT or SL_HIT
            price: Trigger price
            pnl: P&L amount

        Returns:
            True if successful, False otherwise
        """
        config = self._get_config()
        if not config or not config.get("gtt_alerts_enabled"):
            return False

        pnl_emoji = "✅" if pnl >= 0 else "❌"
        pnl_sign = "+" if pnl >= 0 else ""

        message = f"""🎯 <b>GTT TRIGGERED - {account_name}</b>

Stock: {stock}
Type: {trigger_type}
Price: ₹{price:.2f}
P&L: {pnl_sign}₹{pnl:.2f} {pnl_emoji}

Time: {datetime.now().strftime('%H:%M:%S')}"""

        return self._send_alert("GTT_TRIGGERED", message)

    def send_big_loss_alert(
        self,
        account_id: int,
        account_name: str,
        stock: str,
        loss_pct: float,
        loss_amount: float,
        current_price: float,
        avg_price: float
    ) -> bool:
        """
        Send alert when stock drops below loss threshold

        Args:
            account_id: Account ID
            account_name: Account name
            stock: Stock symbol
            loss_pct: Loss percentage
            loss_amount: Loss amount in rupees
            current_price: Current price
            avg_price: Average buy price

        Returns:
            True if successful, False otherwise
        """
        config = self._get_config()
        if not config or not config.get("loss_alerts_enabled"):
            return False

        message = f"""⚠️ <b>BIG LOSS ALERT - {account_name}</b>

Stock: {stock}
Loss: {loss_pct:.2f}% (₹{loss_amount:.2f})
Current: ₹{current_price:.2f} | Avg: ₹{avg_price:.2f}

<b>Action: Consider reviewing position</b>

Time: {datetime.now().strftime('%H:%M:%S')}"""

        return self._send_alert("BIG_LOSS", message)

    def send_daily_summary(self, accounts_data: List[Dict[str, Any]]) -> bool:
        """
        Send daily portfolio summary

        Args:
            accounts_data: List of account data with portfolio info

        Returns:
            True if successful, False otherwise
        """
        config = self._get_config()
        if not config or not config.get("daily_summary_enabled"):
            return False

        # Calculate totals
        total_value = sum(a.get("total_value", 0) for a in accounts_data)
        day_pnl = sum(a.get("day_pnl", 0) for a in accounts_data)
        overall_pnl = sum(a.get("overall_pnl", 0) for a in accounts_data)
        investment_value = sum(a.get("investment_value", 0) for a in accounts_data)

        day_pnl_pct = (day_pnl / investment_value * 100) if investment_value > 0 else 0

        # Get top gainer and loser
        all_stocks = []
        for account in accounts_data:
            all_stocks.extend(account.get("stocks", []))

        top_gainer = max(all_stocks, key=lambda x: x.get("pnl_percent", 0)) if all_stocks else None
        top_loser = min(all_stocks, key=lambda x: x.get("pnl_percent", 0)) if all_stocks else None

        gtt_count = sum(a.get("active_gtt", 0) for a in accounts_data)

        day_pnl_sign = "+" if day_pnl >= 0 else ""
        overall_pnl_sign = "+" if overall_pnl >= 0 else ""

        message = f"""📊 <b>DAILY SUMMARY - {datetime.now().strftime('%Y-%m-%d')}</b>
━━━━━━━━━━━━━━

Total Portfolio: ₹{total_value:,.2f}
Day P&L: {day_pnl_sign}₹{day_pnl:,.2f} ({day_pnl_sign}{day_pnl_pct:.2f}%)
Overall P&L: {overall_pnl_sign}₹{overall_pnl:,.2f}
Active GTT: {gtt_count}
━━━━━━━━━━━━━━"""

        if top_gainer:
            message += f"\nTop Gainer: {top_gainer['stock']} +{top_gainer['pnl_percent']:.2f}%"
        if top_loser:
            message += f"\nTop Loser: {top_loser['stock']} {top_loser['pnl_percent']:.2f}%"

        return self._send_alert("DAILY_SUMMARY", message)

    def send_morning_summary(self, accounts_data: List[Dict[str, Any]]) -> bool:
        """
        Send morning portfolio summary before market open

        Args:
            accounts_data: List of account data with portfolio info

        Returns:
            True if successful, False otherwise
        """
        config = self._get_config()
        if not config or not config.get("daily_summary_enabled"):
            return False

        total_value = sum(a.get("total_value", 0) for a in accounts_data)
        overall_pnl = sum(a.get("overall_pnl", 0) for a in accounts_data)
        holdings_count = sum(a.get("holdings_count", 0) for a in accounts_data)

        overall_pnl_sign = "+" if overall_pnl >= 0 else ""

        message = f"""🌅 <b>MORNING SUMMARY - {datetime.now().strftime('%Y-%m-%d')}</b>
━━━━━━━━━━━━━━

Portfolio Value: ₹{total_value:,.2f}
Overall P&L: {overall_pnl_sign}₹{overall_pnl:,.2f}
Total Holdings: {holdings_count}

Market opens in 5 minutes! 📈"""

        return self._send_alert("MORNING_SUMMARY", message)

    def send_order_placed_alert(
        self,
        account_id: int,
        account_name: str,
        stock: str,
        qty: int,
        price: float,
        order_type: str,
        transaction_type: str
    ) -> bool:
        """
        Send alert when order is placed

        Args:
            account_id: Account ID
            account_name: Account name
            stock: Stock symbol
            qty: Quantity
            price: Price
            order_type: Order type (MARKET, LIMIT, etc.)
            transaction_type: BUY or SELL

        Returns:
            True if successful, False otherwise
        """
        config = self._get_config()
        if not config or not config.get("order_alerts_enabled"):
            return False

        emoji = "🟢" if transaction_type == "BUY" else "🔴"

        message = f"""{emoji} <b>ORDER PLACED - {account_name}</b>

Stock: {stock}
Type: {transaction_type} {order_type}
Qty: {qty}
Price: ₹{price:.2f}

Time: {datetime.now().strftime('%H:%M:%S')}"""

        return self._send_alert("ORDER_PLACED", message)

    def send_order_cancelled_alert(
        self,
        account_id: int,
        account_name: str,
        stock: str,
        order_id: str
    ) -> bool:
        """
        Send alert when order is cancelled

        Args:
            account_id: Account ID
            account_name: Account name
            stock: Stock symbol
            order_id: Order ID

        Returns:
            True if successful, False otherwise
        """
        config = self._get_config()
        if not config or not config.get("order_alerts_enabled"):
            return False

        message = f"""🚫 <b>ORDER CANCELLED - {account_name}</b>

Stock: {stock}
Order ID: {order_id}

Time: {datetime.now().strftime('%H:%M:%S')}"""

        return self._send_alert("ORDER_CANCELLED", message)

    def send_portfolio_summary(
        self,
        total_value: float,
        day_pnl: float,
        overall_pnl: float
    ) -> bool:
        """
        Send portfolio summary alert

        Args:
            total_value: Total portfolio value
            day_pnl: Day P&L
            overall_pnl: Overall P&L

        Returns:
            True if successful, False otherwise
        """
        day_pnl_sign = "+" if day_pnl >= 0 else ""
        overall_pnl_sign = "+" if overall_pnl >= 0 else ""

        message = f"""📊 <b>PORTFOLIO SUMMARY</b>

Total Value: ₹{total_value:,.2f}
Day P&L: {day_pnl_sign}₹{day_pnl:,.2f}
Overall P&L: {overall_pnl_sign}₹{overall_pnl:,.2f}

Time: {datetime.now().strftime('%H:%M:%S')}"""

        return self._send_alert("PORTFOLIO_SUMMARY", message)

    def check_big_losses(self, threshold_pct: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Check all holdings for big losses and send alerts

        Args:
            threshold_pct: Loss threshold percentage (uses config default if None)

        Returns:
            List of stocks with big losses
        """
        config = self._get_config()
        if not config or not config.get("loss_alerts_enabled"):
            return []

        threshold = threshold_pct or config.get("loss_threshold_pct", 5.0)

        try:
            from models import Holding, Account

            holdings = self.db.query(Holding).join(Account).filter(
                Account.is_active == True
            ).all()

            big_losses = []

            for holding in holdings:
                if holding.pnl_percent < -threshold:
                    loss_amount = holding.pnl
                    big_losses.append({
                        "account_id": holding.account_id,
                        "account_name": holding.account.name,
                        "stock": holding.stock,
                        "loss_pct": holding.pnl_percent,
                        "loss_amount": loss_amount,
                        "current_price": holding.ltp,
                        "avg_price": holding.avg_price
                    })

                    # Send alert
                    self.send_big_loss_alert(
                        account_id=holding.account_id,
                        account_name=holding.account.name,
                        stock=holding.stock,
                        loss_pct=holding.pnl_percent,
                        loss_amount=loss_amount,
                        current_price=holding.ltp,
                        avg_price=holding.avg_price
                    )

            return big_losses

        except Exception as e:
            logger.error(f"Error checking big losses: {e}")
            return []

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent alert history

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alert history records
        """
        try:
            from models import AlertHistory

            alerts = self.db.query(AlertHistory).order_by(
                AlertHistory.sent_at.desc()
            ).limit(limit).all()

            return [
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "message": alert.message,
                    "sent_at": alert.sent_at.isoformat(),
                    "success": alert.success
                }
                for alert in alerts
            ]
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []

    def test_connection(self) -> Dict[str, Any]:
        """
        Test Telegram connection

        Returns:
            Dict with success status and message
        """
        config = self._get_config()
        if not config or not config.get("chat_id"):
            return {
                "success": False,
                "message": "Telegram not configured. Please set bot token and chat ID."
            }

        test_message = f"""✅ <b>pyPortMan Test Alert</b>

This is a test message from pyPortMan.
Your Telegram alerts are working correctly!

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        success = self.send_message(config["chat_id"], test_message)

        if success:
            return {
                "success": True,
                "message": "Test message sent successfully!"
            }
        else:
            return {
                "success": False,
                "message": "Failed to send test message. Please check your bot token and chat ID."
            }
