"""
Discord Alert System for pyPortMan
Sends notifications for important portfolio events via Discord Webhook

Setup Instructions:
1. Go to your Discord server settings
2. Create a new webhook in the channel where you want alerts
3. Copy the webhook URL
4. Add the webhook URL to AlertConfig or DiscordConfig table
"""

import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

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


class DiscordAlerts:
    """Manager for Discord notifications via webhook"""

    def __init__(self, db: Session):
        self.db = db
        self._webhook_url = None

    def _get_webhook_url(self) -> Optional[str]:
        """Get Discord webhook URL from database"""
        try:
            from models import AlertConfig
            config = self.db.query(AlertConfig).first()
            if config and hasattr(config, 'discord_webhook_url'):
                return config.discord_webhook_url
        except Exception as e:
            logger.error(f"Error getting Discord webhook URL: {e}")
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

    def send_message(self, webhook_url: str, content: str, embed: Optional[Dict] = None) -> bool:
        """
        Send any message to Discord via webhook

        Args:
            webhook_url: Discord webhook URL
            content: Message content
            embed: Optional embed object for rich formatting

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"content": content}

            if embed:
                payload["embeds"] = [embed]

            response = requests.post(webhook_url, json=payload, timeout=10)

            if response.status_code in [200, 204]:
                return True
            else:
                logger.error(f"Discord API error: {response.status_code} - {response.text}")
                return False

        except requests.RequestException as e:
            logger.error(f"Error sending Discord message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord message: {e}")
            return False

    def _send_alert(self, alert_type: str, content: str, embed: Optional[Dict] = None) -> bool:
        """
        Internal method to send alert with logging

        Args:
            alert_type: Type of alert (GTT_TRIGGERED, BIG_LOSS, etc.)
            content: Formatted message content
            embed: Optional embed for rich formatting

        Returns:
            True if successful, False otherwise
        """
        webhook_url = self._get_webhook_url()
        if not webhook_url:
            logger.warning("Discord webhook not configured")
            self._log_alert(alert_type, content, False)
            return False

        success = self.send_message(webhook_url, content, embed)
        self._log_alert(alert_type, content, success)
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
        pnl_emoji = "✅" if pnl >= 0 else "❌"
        pnl_sign = "+" if pnl >= 0 else ""

        content = f"🎯 **GTT TRIGGERED - {account_name}**\n\n" \
                 f"Stock: {stock}\n" \
                 f"Type: {trigger_type}\n" \
                 f"Price: ₹{price:.2f}\n" \
                 f"P&L: {pnl_sign}₹{pnl:.2f} {pnl_emoji}\n\n" \
                 f"Time: {datetime.now().strftime('%H:%M:%S')}"

        embed = {
            "title": f"GTT Triggered - {stock}",
            "color": 0x00ff00 if pnl >= 0 else 0xff0000,
            "fields": [
                {"name": "Account", "value": account_name, "inline": True},
                {"name": "Trigger Type", "value": trigger_type, "inline": True},
                {"name": "Price", "value": f"₹{price:.2f}", "inline": True},
                {"name": "P&L", "value": f"{pnl_sign}₹{pnl:.2f}", "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_alert("GTT_TRIGGERED", content, embed)

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
        content = f"⚠️ **BIG LOSS ALERT - {account_name}**\n\n" \
                 f"Stock: {stock}\n" \
                 f"Loss: {loss_pct:.2f}% (₹{loss_amount:.2f})\n" \
                 f"Current: ₹{current_price:.2f} | Avg: ₹{avg_price:.2f}\n\n" \
                 f"**Action: Consider reviewing position**\n\n" \
                 f"Time: {datetime.now().strftime('%H:%M:%S')}"

        embed = {
            "title": f"Big Loss Alert - {stock}",
            "color": 0xff0000,
            "fields": [
                {"name": "Account", "value": account_name, "inline": True},
                {"name": "Loss %", "value": f"{loss_pct:.2f}%", "inline": True},
                {"name": "Loss Amount", "value": f"₹{loss_amount:.2f}", "inline": True},
                {"name": "Current Price", "value": f"₹{current_price:.2f}", "inline": True},
                {"name": "Avg Price", "value": f"₹{avg_price:.2f}", "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_alert("BIG_LOSS", content, embed)

    def send_profit_threshold_alert(
        self,
        account_id: int,
        account_name: str,
        stock: str,
        profit_pct: float,
        profit_amount: float,
        current_price: float,
        avg_price: float
    ) -> bool:
        """
        Send alert when stock hits profit threshold

        Args:
            account_id: Account ID
            account_name: Account name
            stock: Stock symbol
            profit_pct: Profit percentage
            profit_amount: Profit amount in rupees
            current_price: Current price
            avg_price: Average buy price

        Returns:
            True if successful, False otherwise
        """
        content = f"🎉 **PROFIT TARGET HIT - {account_name}**\n\n" \
                 f"Stock: {stock}\n" \
                 f"Profit: +{profit_pct:.2f}% (+₹{profit_amount:.2f})\n" \
                 f"Current: ₹{current_price:.2f} | Avg: ₹{avg_price:.2f}\n\n" \
                 f"**Action: Consider booking profits or trailing stop-loss**\n\n" \
                 f"Time: {datetime.now().strftime('%H:%M:%S')}"

        embed = {
            "title": f"Profit Target Hit - {stock}",
            "color": 0x00ff00,
            "fields": [
                {"name": "Account", "value": account_name, "inline": True},
                {"name": "Profit %", "value": f"+{profit_pct:.2f}%", "inline": True},
                {"name": "Profit Amount", "value": f"+₹{profit_amount:.2f}", "inline": True},
                {"name": "Current Price", "value": f"₹{current_price:.2f}", "inline": True},
                {"name": "Avg Price", "value": f"₹{avg_price:.2f}", "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_alert("PROFIT_THRESHOLD", content, embed)

    def send_technical_alert(
        self,
        stock: str,
        indicator: str,
        signal: str,
        current_price: float,
        details: Dict[str, Any]
    ) -> bool:
        """
        Send alert for technical indicator signal

        Args:
            stock: Stock symbol
            indicator: Indicator name (RSI, MACD, etc.)
            signal: Signal type (buy, sell, hold)
            current_price: Current price
            details: Additional details from indicator

        Returns:
            True if successful, False otherwise
        """
        emoji = "🟢" if "buy" in signal else "🔴" if "sell" in signal else "⚪"
        color = 0x00ff00 if "buy" in signal else 0xff0000 if "sell" in signal else 0xffff00

        content = f"{emoji} **TECHNICAL ALERT - {stock}**\n\n" \
                 f"Indicator: {indicator.upper()}\n" \
                 f"Signal: {signal.upper()}\n" \
                 f"Current Price: ₹{current_price:.2f}\n\n" \
                 f"Time: {datetime.now().strftime('%H:%M:%S')}"

        embed = {
            "title": f"Technical Alert - {stock}",
            "color": color,
            "fields": [
                {"name": "Indicator", "value": indicator.upper(), "inline": True},
                {"name": "Signal", "value": signal.upper(), "inline": True},
                {"name": "Current Price", "value": f"₹{current_price:.2f}", "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_alert(f"TECHNICAL_{indicator.upper()}", content, embed)

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
        emoji = "🟢" if transaction_type == "BUY" else "🔴"
        color = 0x00ff00 if transaction_type == "BUY" else 0xff0000

        content = f"{emoji} **ORDER PLACED - {account_name}**\n\n" \
                 f"Stock: {stock}\n" \
                 f"Type: {transaction_type} {order_type}\n" \
                 f"Qty: {qty}\n" \
                 f"Price: ₹{price:.2f}\n\n" \
                 f"Time: {datetime.now().strftime('%H:%M:%S')}"

        embed = {
            "title": f"Order Placed - {stock}",
            "color": color,
            "fields": [
                {"name": "Account", "value": account_name, "inline": True},
                {"name": "Type", "value": f"{transaction_type} {order_type}", "inline": True},
                {"name": "Quantity", "value": str(qty), "inline": True},
                {"name": "Price", "value": f"₹{price:.2f}", "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_alert("ORDER_PLACED", content, embed)

    def send_daily_summary(self, accounts_data: List[Dict[str, Any]]) -> bool:
        """
        Send daily portfolio summary

        Args:
            accounts_data: List of account data with portfolio info

        Returns:
            True if successful, False otherwise
        """
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
        color = 0x00ff00 if day_pnl >= 0 else 0xff0000

        content = f"📊 **DAILY SUMMARY - {datetime.now().strftime('%Y-%m-%d')}**\n" \
                 f"━━━━━━━━━━━━━━\n\n" \
                 f"Total Portfolio: ₹{total_value:,.2f}\n" \
                 f"Day P&L: {day_pnl_sign}₹{day_pnl:,.2f} ({day_pnl_sign}{day_pnl_pct:.2f}%)\n" \
                 f"Overall P&L: {overall_pnl_sign}₹{overall_pnl:,.2f}\n" \
                 f"Active GTT: {gtt_count}\n" \
                 f"━━━━━━━━━━━━━━"

        if top_gainer:
            content += f"\nTop Gainer: {top_gainer['stock']} +{top_gainer['pnl_percent']:.2f}%"
        if top_loser:
            content += f"\nTop Loser: {top_loser['stock']} {top_loser['pnl_percent']:.2f}%"

        embed = {
            "title": f"Daily Summary - {datetime.now().strftime('%Y-%m-%d')}",
            "color": color,
            "fields": [
                {"name": "Total Portfolio", "value": f"₹{total_value:,.2f}", "inline": True},
                {"name": "Day P&L", "value": f"{day_pnl_sign}₹{day_pnl:,.2f}", "inline": True},
                {"name": "Day P&L %", "value": f"{day_pnl_sign}{day_pnl_pct:.2f}%", "inline": True},
                {"name": "Overall P&L", "value": f"{overall_pnl_sign}₹{overall_pnl:,.2f}", "inline": True},
                {"name": "Active GTT", "value": str(gtt_count), "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_alert("DAILY_SUMMARY", content, embed)

    def test_connection(self) -> Dict[str, Any]:
        """
        Test Discord webhook connection

        Returns:
            Dict with success status and message
        """
        webhook_url = self._get_webhook_url()
        if not webhook_url:
            return {
                "success": False,
                "message": "Discord webhook not configured. Please set webhook URL in AlertConfig."
            }

        content = f"✅ **pyPortMan Test Alert**\n\n" \
                  f"This is a test message from pyPortMan.\n" \
                  f"Your Discord alerts are working correctly!\n\n" \
                  f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        embed = {
            "title": "Test Alert",
            "description": "Your Discord webhook is working correctly!",
            "color": 0x00ff00,
            "timestamp": datetime.utcnow().isoformat()
        }

        success = self.send_message(webhook_url, content, embed)

        if success:
            return {
                "success": True,
                "message": "Test message sent successfully!"
            }
        else:
            return {
                "success": False,
                "message": "Failed to send test message. Please check your webhook URL."
            }
