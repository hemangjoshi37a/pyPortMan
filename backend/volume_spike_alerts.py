"""
Volume Spike Alerts Manager for pyPortMan
Detect unusual trading activity
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, VolumeSpikeAlert, Holding
from kite_manager import KiteManager

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


class VolumeSpikeAlertsManager:
    """Manager for volume spike alerts"""

    def __init__(self, db: Session):
        self.db = db
        self.kite_manager = KiteManager(db)

    def create_alert(
        self,
        account_id: int,
        stock: str,
        exchange: str,
        avg_volume_period: int,
        volume_multiplier: float,
        min_volume: int = 10000,
        repeat: bool = False,
        repeat_interval_hours: int = 24
    ) -> VolumeSpikeAlert:
        """
        Create a new volume spike alert
        """
        alert = VolumeSpikeAlert(
            account_id=account_id,
            stock=stock,
            exchange=exchange,
            avg_volume_period=avg_volume_period,
            volume_multiplier=volume_multiplier,
            min_volume=min_volume,
            repeat=repeat,
            repeat_interval_hours=repeat_interval_hours,
            status="ACTIVE"
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Created volume spike alert for {stock}")
        return alert

    def update_alert(
        self,
        alert_id: int,
        **kwargs
    ) -> VolumeSpikeAlert:
        """
        Update an existing volume spike alert
        """
        alert = self.db.query(VolumeSpikeAlert).filter(
            VolumeSpikeAlert.id == alert_id
        ).first()

        if not alert:
            raise ValueError(f"Volume spike alert {alert_id} not found")

        # Update provided fields
        for field, value in kwargs.items():
            if hasattr(alert, field) and value is not None:
                setattr(alert, field, value)

        alert.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Updated volume spike alert {alert_id}")
        return alert

    def cancel_alert(self, alert_id: int) -> bool:
        """
        Cancel a volume spike alert
        """
        alert = self.db.query(VolumeSpikeAlert).filter(
            VolumeSpikeAlert.id == alert_id
        ).first()

        if not alert:
            raise ValueError(f"Volume spike alert {alert_id} not found")

        alert.status = "CANCELLED"
        alert.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Cancelled volume spike alert {alert_id}")
        return True

    def check_volume_spikes(self, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Check all active volume spike alerts
        Returns list of triggered alerts
        """
        query = self.db.query(VolumeSpikeAlert).filter(
            VolumeSpikeAlert.status == "ACTIVE"
        )

        if account_id:
            query = query.filter(VolumeSpikeAlert.account_id == account_id)

        alerts = query.all()
        triggered = []

        for alert in alerts:
            try:
                # Get current quote with volume
                quote = self.kite_manager.fetch_stock_quote(
                    alert.account_id,
                    alert.stock,
                    alert.exchange
                )

                if not quote:
                    continue

                current_volume = quote.get("volume", 0)

                # Check if volume meets minimum threshold
                if current_volume < alert.min_volume:
                    continue

                # Calculate average volume (simplified - in production, use historical data)
                avg_volume = self._calculate_average_volume(
                    alert.account_id,
                    alert.stock,
                    alert.exchange,
                    alert.avg_volume_period
                )

                # Check if volume spike detected
                if avg_volume > 0 and current_volume >= avg_volume * alert.volume_multiplier:
                    # Check repeat interval
                    if alert.repeat and alert.triggered_at:
                        time_since_trigger = datetime.utcnow() - alert.triggered_at
                        if time_since_trigger.total_seconds() < alert.repeat_interval_hours * 3600:
                            continue

                    # Trigger alert
                    alert.status = "TRIGGERED"
                    alert.triggered_at = datetime.utcnow()
                    alert.triggered_volume = current_volume
                    alert.avg_volume = avg_volume
                    self.db.commit()

                    triggered.append({
                        "id": alert.id,
                        "stock": alert.stock,
                        "current_volume": current_volume,
                        "avg_volume": avg_volume,
                        "multiplier": alert.volume_multiplier,
                        "spike_ratio": current_volume / avg_volume if avg_volume > 0 else 0
                    })

                    logger.warning(f"Volume spike detected for {alert.stock}: {current_volume} vs avg {avg_volume}")

            except Exception as e:
                logger.error(f"Error checking volume spike for {alert.stock}: {e}")

        return triggered

    def _calculate_average_volume(
        self,
        account_id: int,
        stock: str,
        exchange: str,
        period_days: int
    ) -> int:
        """
        Calculate average volume over a period
        In production, this would use historical data
        """
        # For now, return a simplified average
        # In production, fetch historical data and calculate actual average
        try:
            # Get historical data
            from_date = datetime.utcnow() - timedelta(days=period_days)
            candles = self.kite_manager.fetch_historical_data(
                account_id,
                stock,
                exchange,
                "day",
                from_date,
                datetime.utcnow()
            )

            if candles:
                volumes = [c.get("volume", 0) for c in candles]
                return sum(volumes) // len(volumes) if volumes else 0

        except Exception as e:
            logger.error(f"Error calculating average volume: {e}")

        return 0

    def get_alerts(
        self,
        account_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[VolumeSpikeAlert]:
        """
        Get volume spike alerts with optional filters
        """
        query = self.db.query(VolumeSpikeAlert)

        if account_id:
            query = query.filter(VolumeSpikeAlert.account_id == account_id)

        if status:
            query = query.filter(VolumeSpikeAlert.status == status)

        return query.order_by(VolumeSpikeAlert.created_at.desc()).all()

    def get_alert_summary(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of volume spike alerts
        """
        query = self.db.query(VolumeSpikeAlert)

        if account_id:
            query = query.filter(VolumeSpikeAlert.account_id == account_id)

        total = query.count()
        active = query.filter(VolumeSpikeAlert.status == "ACTIVE").count()
        triggered = query.filter(VolumeSpikeAlert.status == "TRIGGERED").count()
        cancelled = query.filter(VolumeSpikeAlert.status == "CANCELLED").count()

        return {
            "total": total,
            "active": active,
            "triggered": triggered,
            "cancelled": cancelled
        }

    def get_volume_analysis(
        self,
        account_id: int,
        stock: str,
        exchange: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze volume patterns for a stock
        """
        try:
            # Get historical data
            from_date = datetime.utcnow() - timedelta(days=days)
            candles = self.kite_manager.fetch_historical_data(
                account_id,
                stock,
                exchange,
                "day",
                from_date,
                datetime.utcnow()
            )

            if not candles:
                return {"error": "No historical data available"}

            volumes = [c.get("volume", 0) for c in candles]
            closes = [c.get("close", 0) for c in candles]

            # Calculate statistics
            avg_volume = sum(volumes) // len(volumes) if volumes else 0
            max_volume = max(volumes) if volumes else 0
            min_volume = min(volumes) if volumes else 0

            # Calculate volume trend
            recent_avg = sum(volumes[-5:]) // 5 if len(volumes) >= 5 else avg_volume
            older_avg = sum(volumes[:-5]) // (len(volumes) - 5) if len(volumes) > 5 else avg_volume
            volume_trend = (recent_avg - older_avg) / older_avg * 100 if older_avg > 0 else 0

            # Price-volume correlation (simplified)
            price_change = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0

            return {
                "stock": stock,
                "period_days": days,
                "avg_volume": avg_volume,
                "max_volume": max_volume,
                "min_volume": min_volume,
                "current_volume": volumes[-1] if volumes else 0,
                "volume_trend_pct": volume_trend,
                "price_change_pct": price_change,
                "volume_ratio": volumes[-1] / avg_volume if avg_volume > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error analyzing volume for {stock}: {e}")
            return {"error": str(e)}

    def detect_unusual_activity(
        self,
        account_id: int,
        threshold_multiplier: float = 3.0
    ) -> List[Dict[str, Any]]:
        """
        Detect unusual volume activity across all holdings
        """
        holdings = self.db.query(Holding).filter(
            Holding.account_id == account_id
        ).all()

        unusual_activity = []

        for holding in holdings:
            try:
                analysis = self.get_volume_analysis(
                    account_id,
                    holding.stock,
                    holding.exchange,
                    30
                )

                if "error" not in analysis:
                    volume_ratio = analysis.get("volume_ratio", 0)

                    if volume_ratio >= threshold_multiplier:
                        unusual_activity.append({
                            "stock": holding.stock,
                            "volume_ratio": volume_ratio,
                            "current_volume": analysis.get("current_volume"),
                            "avg_volume": analysis.get("avg_volume"),
                            "price_change_pct": analysis.get("price_change_pct")
                        })

            except Exception as e:
                logger.error(f"Error detecting unusual activity for {holding.stock}: {e}")

        return unusual_activity
