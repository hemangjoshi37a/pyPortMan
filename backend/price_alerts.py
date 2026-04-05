"""
Price Alerts Manager for pyPortMan Backend
Custom price alerts on any stock with Telegram notifications
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import Account, Holding, PriceAlert, AlertHistory
from kite_manager import KiteManager
from telegram_alerts import TelegramAlerts

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


class PriceAlertManager:
    """Manager for custom price alerts on stocks"""

    def __init__(self, db: Session):
        self.db = db
        self.kite_manager = KiteManager(db)
        self.telegram = TelegramAlerts(db)

    def create_alert(self, alert_data: Dict[str, Any]) -> PriceAlert:
        """
        Create a new price alert

        Args:
            alert_data: Dict with alert details
                - account_id: Account ID
                - stock: Trading symbol
                - exchange: Exchange (NSE/BSE)
                - alert_type: 'ABOVE' or 'BELOW'
                - target_price: Target price
                - repeat: Whether to repeat alert (default: False)
                - repeat_interval: Repeat interval in hours (default: 24)

        Returns:
            Created PriceAlert object
        """
        alert = PriceAlert(
            account_id=alert_data.get("account_id"),
            stock=alert_data.get("stock"),
            exchange=alert_data.get("exchange", "NSE"),
            alert_type=alert_data.get("alert_type", "ABOVE"),
            target_price=alert_data.get("target_price"),
            current_price=0,
            repeat=alert_data.get("repeat", False),
            repeat_interval=alert_data.get("repeat_interval", 24),
            status="ACTIVE",
            created_at=datetime.utcnow()
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Created price alert for {alert.stock} at {alert.target_price}")
        return alert

    def update_alert(self, alert_id: int, alert_data: Dict[str, Any]) -> Optional[PriceAlert]:
        """
        Update an existing price alert

        Args:
            alert_id: Alert ID
            alert_data: Dict with fields to update

        Returns:
            Updated PriceAlert object or None
        """
        alert = self.db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if not alert:
            logger.error(f"Alert {alert_id} not found")
            return None

        for field, value in alert_data.items():
            if hasattr(alert, field) and value is not None:
                setattr(alert, field, value)

        alert.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Updated price alert {alert_id}")
        return alert

    def delete_alert(self, alert_id: int) -> bool:
        """
        Delete a price alert

        Args:
            alert_id: Alert ID

        Returns:
            True if successful
        """
        alert = self.db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if not alert:
            logger.error(f"Alert {alert_id} not found")
            return False

        self.db.delete(alert)
        self.db.commit()

        logger.info(f"Deleted price alert {alert_id}")
        return True

    def get_alerts(self, account_id: Optional[int] = None, status: str = "ACTIVE") -> List[PriceAlert]:
        """
        Get price alerts

        Args:
            account_id: Filter by account ID (optional)
            status: Filter by status (default: ACTIVE)

        Returns:
            List of PriceAlert objects
        """
        query = self.db.query(PriceAlert).filter(PriceAlert.status == status)

        if account_id:
            query = query.filter(PriceAlert.account_id == account_id)

        return query.order_by(PriceAlert.created_at.desc()).all()

    def get_alert(self, alert_id: int) -> Optional[PriceAlert]:
        """
        Get a specific price alert

        Args:
            alert_id: Alert ID

        Returns:
            PriceAlert object or None
        """
        return self.db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check all active alerts and trigger if conditions are met

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        active_alerts = self.db.query(PriceAlert).filter(PriceAlert.status == "ACTIVE").all()

        for alert in active_alerts:
            try:
                # Get current price for the stock
                current_price = self._get_current_price(alert.stock, alert.exchange, alert.account_id)

                if current_price is None:
                    logger.warning(f"Could not get price for {alert.stock}")
                    continue

                # Update current price in alert
                alert.current_price = current_price
                alert.last_checked_at = datetime.utcnow()

                # Check if alert condition is met
                triggered = False
                if alert.alert_type == "ABOVE" and current_price >= alert.target_price:
                    triggered = True
                elif alert.alert_type == "BELOW" and current_price <= alert.target_price:
                    triggered = True

                if triggered:
                    # Trigger the alert
                    result = self._trigger_alert(alert, current_price)
                    triggered_alerts.append(result)

                    # Update alert status
                    if alert.repeat:
                        # Calculate next trigger time
                        alert.next_trigger_at = datetime.utcnow() + timedelta(hours=alert.repeat_interval)
                        alert.triggered_count = (alert.triggered_count or 0) + 1
                    else:
                        # Mark as completed
                        alert.status = "TRIGGERED"
                        alert.triggered_at = datetime.utcnow()

                    self.db.commit()

            except Exception as e:
                logger.error(f"Error checking alert {alert.id}: {e}")

        return triggered_alerts

    def _get_current_price(self, stock: str, exchange: str, account_id: int) -> Optional[float]:
        """
        Get current price for a stock

        Args:
            stock: Trading symbol
            exchange: Exchange
            account_id: Account ID to use for API

        Returns:
            Current price or None
        """
        try:
            kite = self.kite_manager.get_kite(account_id)
            if not kite:
                logger.error(f"Could not get Kite instance for account {account_id}")
                return None

            # Get quote for the stock
            quote = kite.quote(f"{exchange}:{stock}")
            if quote and stock in quote:
                return quote[stock].get("last_price")

            return None

        except Exception as e:
            logger.error(f"Error getting price for {stock}: {e}")
            return None

    def _trigger_alert(self, alert: PriceAlert, current_price: float) -> Dict[str, Any]:
        """
        Trigger a price alert and send notification

        Args:
            alert: PriceAlert object
            current_price: Current price that triggered the alert

        Returns:
            Dict with trigger result
        """
        try:
            # Get account details
            account = self.db.query(Account).filter(Account.id == alert.account_id).first()
            if not account:
                logger.error(f"Account {alert.account_id} not found")
                return {"alert_id": alert.id, "success": False, "error": "Account not found"}

            # Calculate price difference
            price_diff = current_price - alert.target_price
            price_diff_pct = (price_diff / alert.target_price * 100) if alert.target_price > 0 else 0

            # Send Telegram notification
            message = (
                f"🔔 PRICE ALERT TRIGGERED!\n\n"
                f"📊 Stock: {alert.stock}\n"
                f"💰 Target Price: ₹{alert.target_price:.2f}\n"
                f"📈 Current Price: ₹{current_price:.2f}\n"
                f"📉 Difference: ₹{price_diff:.2f} ({price_diff_pct:+.2f}%)\n"
                f"🎯 Alert Type: {alert.alert_type}\n"
                f"👤 Account: {account.name}\n"
                f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            success = self.telegram.send_custom_alert(message)

            # Log to alert history
            history = AlertHistory(
                alert_type="PRICE_ALERT",
                message=message,
                sent_at=datetime.utcnow(),
                success=success
            )
            self.db.add(history)
            self.db.commit()

            logger.info(f"Price alert triggered for {alert.stock} at ₹{current_price}")

            return {
                "alert_id": alert.id,
                "success": success,
                "stock": alert.stock,
                "target_price": alert.target_price,
                "current_price": current_price,
                "message": message
            }

        except Exception as e:
            logger.error(f"Error triggering alert {alert.id}: {e}")
            return {"alert_id": alert.id, "success": False, "error": str(e)}

    def get_alert_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of price alerts

        Args:
            account_id: Filter by account ID (optional)

        Returns:
            Dict with summary statistics
        """
        query = self.db.query(PriceAlert)

        if account_id:
            query = query.filter(PriceAlert.account_id == account_id)

        total = query.count()
        active = query.filter(PriceAlert.status == "ACTIVE").count()
        triggered = query.filter(PriceAlert.status == "TRIGGERED").count()
        completed = query.filter(PriceAlert.status == "COMPLETED").count()

        return {
            "total": total,
            "active": active,
            "triggered": triggered,
            "completed": completed
        }

    def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        Clean up old completed alerts

        Args:
            days: Number of days to keep alerts

        Returns:
            Number of alerts deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        deleted = self.db.query(PriceAlert).filter(
            and_(
                PriceAlert.status.in_(["TRIGGERED", "COMPLETED"]),
                PriceAlert.created_at < cutoff_date
            )
        ).delete()

        self.db.commit()
        logger.info(f"Cleaned up {deleted} old alerts")
        return deleted


if __name__ == "__main__":
    # Test price alerts
    from database import SessionLocal

    db = SessionLocal()
    manager = PriceAlertManager(db)

    # Test creating an alert
    test_alert = {
        "account_id": 1,
        "stock": "RELIANCE",
        "exchange": "NSE",
        "alert_type": "ABOVE",
        "target_price": 2500.0,
        "repeat": False
    }

    alert = manager.create_alert(test_alert)
    print(f"Created alert: {alert}")

    db.close()
