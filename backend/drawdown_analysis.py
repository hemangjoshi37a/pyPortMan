"""
Drawdown Analysis Manager for pyPortMan
Visualize maximum drawdown periods
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session

from models import Account, PortfolioSnapshot, DrawdownRecord

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


class DrawdownAnalysisManager:
    """Manager for drawdown analysis"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_drawdowns(
        self,
        account_id: int,
        days: int = 365
    ) -> List[DrawdownRecord]:
        """
        Calculate drawdowns from portfolio snapshots
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get portfolio snapshots
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= cutoff
        ).order_by(
            PortfolioSnapshot.recorded_at.asc()
        ).all()

        if not snapshots:
            return []

        # Find drawdown periods
        drawdowns = []
        peak_value = 0
        peak_date = None
        in_drawdown = False

        for snapshot in snapshots:
            current_value = snapshot.total_value

            # Check if we're at a new peak
            if current_value > peak_value:
                # If we were in a drawdown, mark it as recovered
                if in_drawdown:
                    # Update the last drawdown with recovery date
                    if drawdowns:
                        drawdowns[-1].recovery_date = snapshot.recorded_at
                        drawdowns[-1].duration_days = (snapshot.recorded_at - drawdowns[-1].trough_date).days

                peak_value = current_value
                peak_date = snapshot.recorded_at
                in_drawdown = False

            # Check if we're in a drawdown
            elif current_value < peak_value:
                if not in_drawdown:
                    # Start of a new drawdown
                    in_drawdown = True
                    trough_value = current_value
                    trough_date = snapshot.recorded_at

                    drawdown_amount = peak_value - trough_value
                    drawdown_pct = (drawdown_amount / peak_value * 100) if peak_value > 0 else 0

                    # Only record significant drawdowns (>1%)
                    if drawdown_pct > 1:
                        drawdown = DrawdownRecord(
                            account_id=account_id,
                            peak_value=peak_value,
                            trough_value=trough_value,
                            drawdown_amount=drawdown_amount,
                            drawdown_pct=drawdown_pct,
                            peak_date=peak_date,
                            trough_date=trough_date,
                            duration_days=0,
                            is_current=True
                        )
                        self.db.add(drawdown)
                        drawdowns.append(drawdown)
                else:
                    # Update trough if we're going deeper
                    if current_value < drawdowns[-1].trough_value:
                        drawdowns[-1].trough_value = current_value
                        drawdowns[-1].trough_date = snapshot.recorded_at
                        drawdowns[-1].drawdown_amount = peak_value - current_value
                        drawdowns[-1].drawdown_pct = (drawdowns[-1].drawdown_amount / peak_value * 100) if peak_value > 0 else 0

        # Mark current drawdown if still in one
        if drawdowns and not drawdowns[-1].recovery_date:
            drawdowns[-1].is_current = True
        elif drawdowns:
            for dd in drawdowns:
                dd.is_current = False

        self.db.commit()

        logger.info(f"Calculated {len(drawdowns)} drawdowns for account {account_id}")
        return drawdowns

    def get_current_drawdown(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current drawdown information
        """
        current = self.db.query(DrawdownRecord).filter(
            DrawdownRecord.account_id == account_id,
            DrawdownRecord.is_current == True
        ).first()

        if not current:
            return None

        # Get current portfolio value
        latest_snapshot = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(
            PortfolioSnapshot.recorded_at.desc()
        ).first()

        current_value = latest_snapshot.total_value if latest_snapshot else 0

        return {
            "peak_value": current.peak_value,
            "trough_value": current.trough_value,
            "current_value": current_value,
            "drawdown_amount": current.peak_value - current_value,
            "drawdown_pct": ((current.peak_value - current_value) / current.peak_value * 100) if current.peak_value > 0 else 0,
            "peak_date": current.peak_date.isoformat(),
            "trough_date": current.trough_date.isoformat(),
            "duration_days": (datetime.utcnow() - current.peak_date).days
        }

    def get_max_drawdown(self, account_id: int) -> Dict[str, Any]:
        """
        Get maximum drawdown for an account
        """
        max_dd = self.db.query(DrawdownRecord).filter(
            DrawdownRecord.account_id == account_id
        ).order_by(
            DrawdownRecord.drawdown_pct.desc()
        ).first()

        if not max_dd:
            return {
                "message": "No drawdown data available",
                "max_drawdown_pct": 0,
                "max_drawdown_amount": 0
            }

        return {
            "max_drawdown_pct": max_dd.drawdown_pct,
            "max_drawdown_amount": max_dd.drawdown_amount,
            "peak_value": max_dd.peak_value,
            "trough_value": max_dd.trough_value,
            "peak_date": max_dd.peak_date.isoformat(),
            "trough_date": max_dd.trough_date.isoformat(),
            "duration_days": max_dd.duration_days,
            "recovery_date": max_dd.recovery_date.isoformat() if max_dd.recovery_date else None
        }

    def get_drawdown_history(
        self,
        account_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get historical drawdowns
        """
        drawdowns = self.db.query(DrawdownRecord).filter(
            DrawdownRecord.account_id == account_id
        ).order_by(
            DrawdownRecord.peak_date.desc()
        ).limit(limit).all()

        return [
            {
                "peak_value": dd.peak_value,
                "trough_value": dd.trough_value,
                "drawdown_amount": dd.drawdown_amount,
                "drawdown_pct": dd.drawdown_pct,
                "peak_date": dd.peak_date.isoformat(),
                "trough_date": dd.trough_date.isoformat(),
                "duration_days": dd.duration_days,
                "recovery_date": dd.recovery_date.isoformat() if dd.recovery_date else None,
                "is_current": dd.is_current
            }
            for dd in drawdowns
        ]

    def get_drawdown_summary(self, account_id: int) -> Dict[str, Any]:
        """
        Get summary of drawdown statistics
        """
        drawdowns = self.db.query(DrawdownRecord).filter(
            DrawdownRecord.account_id == account_id
        ).all()

        if not drawdowns:
            return {
                "message": "No drawdown data available",
                "total_drawdowns": 0
            }

        total_drawdowns = len(drawdowns)
        max_drawdown = max(dd.drawdown_pct for dd in drawdowns)
        avg_drawdown = sum(dd.drawdown_pct for dd in drawdowns) / total_drawdown
        avg_duration = sum(dd.duration_days for dd in drawdowns if dd.duration_days > 0) / len([dd for dd in drawdowns if dd.duration_days > 0])

        # Count drawdowns by severity
        severe = len([dd for dd in drawdowns if dd.drawdown_pct >= 20])
        moderate = len([dd for dd in drawdowns if 10 <= dd.drawdown_pct < 20])
        mild = len([dd for dd in drawdowns if 5 <= dd.drawdown_pct < 10])
        minor = len([dd for dd in drawdowns if dd.drawdown_pct < 5])

        return {
            "total_drawdowns": total_drawdowns,
            "max_drawdown_pct": max_drawdown,
            "avg_drawdown_pct": avg_drawdown,
            "avg_duration_days": avg_duration,
            "severity_distribution": {
                "severe": severe,  # >= 20%
                "moderate": moderate,  # 10-20%
                "mild": mild,  # 5-10%
                "minor": minor  # < 5%
            }
        }

    def get_drawdown_chart_data(
        self,
        account_id: int,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Get drawdown data for charting
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get portfolio snapshots
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= cutoff
        ).order_by(
            PortfolioSnapshot.recorded_at.asc()
        ).all()

        if not snapshots:
            return {"message": "No data available"}

        # Calculate running peak and drawdown
        peak = 0
        data = []

        for snapshot in snapshots:
            current_value = snapshot.total_value

            if current_value > peak:
                peak = current_value

            drawdown = peak - current_value
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0

            data.append({
                "date": snapshot.recorded_at.isoformat(),
                "portfolio_value": current_value,
                "peak_value": peak,
                "drawdown_amount": drawdown,
                "drawdown_pct": drawdown_pct
            })

        return {
            "data": data,
            "max_drawdown_pct": max(d["drawdown_pct"] for d in data) if data else 0
        }

    def get_recovery_analysis(self, account_id: int) -> Dict[str, Any]:
        """
        Analyze recovery patterns after drawdowns
        """
        drawdowns = self.db.query(DrawdownRecord).filter(
            DrawdownRecord.account_id == account_id,
            DrawdownRecord.recovery_date.isnot(None)
        ).all()

        if not drawdowns:
            return {"message": "No recovered drawdowns found"}

        # Calculate recovery statistics
        recovery_times = [dd.duration_days for dd in drawdowns if dd.duration_days > 0]

        if recovery_times:
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            max_recovery_time = max(recovery_times)
            min_recovery_time = min(recovery_times)
        else:
            avg_recovery_time = 0
            max_recovery_time = 0
            min_recovery_time = 0

        # Analyze by drawdown severity
        severe_dd = [dd for dd in drawdowns if dd.drawdown_pct >= 20]
        moderate_dd = [dd for dd in drawdowns if 10 <= dd.drawdown_pct < 20]

        severe_recovery = sum(dd.duration_days for dd in severe_dd if dd.duration_days > 0) / len(severe_dd) if severe_dd else 0
        moderate_recovery = sum(dd.duration_days for dd in moderate_dd if dd.duration_days > 0) / len(moderate_dd) if moderate_dd else 0

        return {
            "total_recovered_drawdowns": len(drawdowns),
            "avg_recovery_days": avg_recovery_time,
            "max_recovery_days": max_recovery_time,
            "min_recovery_days": min_recovery_time,
            "severe_drawdown_avg_recovery": severe_recovery,
            "moderate_drawdown_avg_recovery": moderate_recovery
        }
