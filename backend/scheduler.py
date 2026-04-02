"""
Scheduler for pyPortMan Backend
Auto-refreshes data during market hours using APScheduler
"""

import logging
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
from kite_manager import KiteManager
from gtt_manager import GTTManager
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


class MarketScheduler:
    """Scheduler for auto-refreshing portfolio data during market hours"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

        # Market hours: 9:15 AM - 3:30 PM IST
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)

    def is_market_hours(self) -> bool:
        """Check if current time is within market hours (weekdays only)"""
        now = datetime.now()
        current_time = now.time()

        # Check if it's a weekday (Monday=0, Friday=4)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check if within market hours
        return self.market_start <= current_time <= self.market_end

    def refresh_account_data(self, account_id: int):
        """Refresh holdings, positions, and orders for a specific account"""
        if not self.is_market_hours():
            logger.info(f"Skipping refresh for account {account_id} - outside market hours")
            return

        try:
            db = SessionLocal()
            kite_manager = KiteManager(db)

            logger.info(f"Refreshing data for account {account_id}")
            kite_manager.refresh_all_data(account_id)

            db.close()
        except Exception as e:
            logger.error(f"Error refreshing data for account {account_id}: {e}")

    def save_portfolio_snapshot(self, account_id: int):
        """Save portfolio snapshot for equity curve tracking"""
        if not self.is_market_hours():
            logger.info(f"Skipping snapshot for account {account_id} - outside market hours")
            return

        try:
            db = SessionLocal()
            kite_manager = KiteManager(db)

            logger.info(f"Saving portfolio snapshot for account {account_id}")
            kite_manager.save_portfolio_snapshot(account_id)

            db.close()
        except Exception as e:
            logger.error(f"Error saving snapshot for account {account_id}: {e}")

    def refresh_all_accounts(self):
        """Refresh data for all active accounts"""
        try:
            db = SessionLocal()
            from models import Account

            accounts = db.query(Account).filter(Account.is_active == True).all()

            for account in accounts:
                self.refresh_account_data(account.id)

            db.close()
        except Exception as e:
            logger.error(f"Error refreshing all accounts: {e}")

    def save_all_snapshots(self):
        """Save portfolio snapshots for all active accounts"""
        try:
            db = SessionLocal()
            from models import Account

            accounts = db.query(Account).filter(Account.is_active == True).all()

            for account in accounts:
                self.save_portfolio_snapshot(account.id)

            db.close()
        except Exception as e:
            logger.error(f"Error saving all snapshots: {e}")

    def check_big_losses(self):
        """Check for big losses in all holdings and send alerts"""
        if not self.is_market_hours():
            logger.info("Skipping big loss check - outside market hours")
            return

        try:
            db = SessionLocal()
            telegram = TelegramAlerts(db)
            losses = telegram.check_big_losses()
            if losses:
                logger.info(f"Found {len(losses)} stocks with big losses")
            db.close()
        except Exception as e:
            logger.error(f"Error checking big losses: {e}")

    def sync_gtt_and_alert(self):
        """Sync GTT status and send triggered alerts"""
        if not self.is_market_hours():
            logger.info("Skipping GTT sync - outside market hours")
            return

        try:
            db = SessionLocal()
            gtt_manager = GTTManager(db, KiteManager(db))
            telegram = TelegramAlerts(db)

            # Get all GTT orders before sync
            from models import GTTOrder
            before_sync = {g.gtt_id: g.status for g in db.query(GTTOrder).all()}

            # Sync GTT status
            result = gtt_manager.sync_gtt_status()

            # Check for newly triggered GTTs
            after_sync = {g.gtt_id: g.status for g in db.query(GTTOrder).all()}

            for gtt_id, new_status in after_sync.items():
                old_status = before_sync.get(gtt_id)
                if old_status != "TRIGGERED" and new_status == "TRIGGERED":
                    # GTT was just triggered
                    gtt = db.query(GTTOrder).filter(GTTOrder.gtt_id == gtt_id).first()
                    if gtt:
                        from models import Account
                        account = db.query(Account).filter(Account.id == gtt.account_id).first()
                        if account:
                            # Determine trigger type (target or SL)
                            trigger_type = "TARGET HIT" if gtt.ltp >= gtt.target_price else "SL HIT"
                            pnl = (gtt.ltp - gtt.buy_price) * gtt.qty

                            telegram.send_gtt_triggered_alert(
                                account_id=gtt.account_id,
                                account_name=account.name,
                                stock=gtt.stock,
                                trigger_type=trigger_type,
                                price=gtt.ltp,
                                pnl=pnl
                            )
                            logger.info(f"Sent GTT triggered alert for {gtt.stock}")

            db.close()
        except Exception as e:
            logger.error(f"Error syncing GTT and sending alerts: {e}")

    def send_morning_summary(self):
        """Send morning summary at 9:10 AM IST"""
        try:
            db = SessionLocal()
            telegram = TelegramAlerts(db)

            # Get all accounts data
            from models import Account, Holding
            accounts = db.query(Account).filter(Account.is_active == True).all()

            accounts_data = []
            for account in accounts:
                holdings = db.query(Holding).filter(Holding.account_id == account.id).all()
                total_value = sum(h.current_value for h in holdings)
                overall_pnl = sum(h.pnl for h in holdings)
                holdings_count = len(holdings)

                accounts_data.append({
                    "total_value": total_value,
                    "overall_pnl": overall_pnl,
                    "holdings_count": holdings_count
                })

            if accounts_data:
                telegram.send_morning_summary(accounts_data)
                logger.info("Morning summary sent")

            db.close()
        except Exception as e:
            logger.error(f"Error sending morning summary: {e}")

    def send_daily_summary(self):
        """Send daily summary at 3:35 PM IST"""
        try:
            db = SessionLocal()
            telegram = TelegramAlerts(db)

            # Get all accounts data
            from models import Account, Holding, GTTOrder
            accounts = db.query(Account).filter(Account.is_active == True).all()

            accounts_data = []
            for account in accounts:
                holdings = db.query(Holding).filter(Holding.account_id == account.id).all()
                total_value = sum(h.current_value for h in holdings)
                investment_value = sum(h.qty * h.avg_price for h in holdings)
                day_pnl = sum(h.pnl for h in holdings)
                overall_pnl = sum(h.pnl for h in holdings)

                # Get active GTT count
                active_gtt = db.query(GTTOrder).filter(
                    GTTOrder.account_id == account.id,
                    GTTOrder.status == "ACTIVE"
                ).count()

                # Get stock details
                stocks = [
                    {
                        "stock": h.stock,
                        "pnl": h.pnl,
                        "pnl_percent": h.pnl_percent
                    }
                    for h in holdings
                ]

                accounts_data.append({
                    "total_value": total_value,
                    "investment_value": investment_value,
                    "day_pnl": day_pnl,
                    "overall_pnl": overall_pnl,
                    "active_gtt": active_gtt,
                    "stocks": stocks
                })

            if accounts_data:
                telegram.send_daily_summary(accounts_data)
                logger.info("Daily summary sent")

            db.close()
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        # Refresh holdings and positions every 5 minutes during market hours
        self.scheduler.add_job(
            self.refresh_all_accounts,
            trigger=IntervalTrigger(minutes=5),
            id='refresh_all_accounts',
            name='Refresh all accounts data',
            replace_existing=True
        )

        # Save portfolio snapshots every 15 minutes during market hours
        self.scheduler.add_job(
            self.save_all_snapshots,
            trigger=IntervalTrigger(minutes=15),
            id='save_all_snapshots',
            name='Save portfolio snapshots',
            replace_existing=True
        )

        # Check for big losses every 15 minutes during market hours
        self.scheduler.add_job(
            self.check_big_losses,
            trigger=IntervalTrigger(minutes=15),
            id='check_big_losses',
            name='Check for big losses',
            replace_existing=True
        )

        # Sync GTT status and send triggered alerts every 5 minutes during market hours
        self.scheduler.add_job(
            self.sync_gtt_and_alert,
            trigger=IntervalTrigger(minutes=5),
            id='sync_gtt_and_alert',
            name='Sync GTT and send alerts',
            replace_existing=True
        )

        # Send morning summary at 9:10 AM IST daily
        self.scheduler.add_job(
            self.send_morning_summary,
            trigger=CronTrigger(hour=9, minute=10),
            id='morning_summary',
            name='Send morning summary',
            replace_existing=True
        )

        # Send daily summary at 3:35 PM IST daily
        self.scheduler.add_job(
            self.send_daily_summary,
            trigger=CronTrigger(hour=15, minute=35),
            id='daily_summary',
            name='Send daily summary',
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True
        logger.info("Scheduler started successfully")

    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Scheduler stopped")

    def add_account_job(self, account_id: int):
        """Add jobs for a new account"""
        # Refresh data for this account every 5 minutes
        self.scheduler.add_job(
            self.refresh_account_data,
            trigger=IntervalTrigger(minutes=5),
            args=[account_id],
            id=f'refresh_account_{account_id}',
            name=f'Refresh account {account_id} data',
            replace_existing=True
        )

        # Save snapshot for this account every 15 minutes
        self.scheduler.add_job(
            self.save_portfolio_snapshot,
            trigger=IntervalTrigger(minutes=15),
            args=[account_id],
            id=f'snapshot_account_{account_id}',
            name=f'Save snapshot for account {account_id}',
            replace_existing=True
        )

        logger.info(f"Added jobs for account {account_id}")

    def remove_account_job(self, account_id: int):
        """Remove jobs for an account"""
        try:
            self.scheduler.remove_job(f'refresh_account_{account_id}')
            self.scheduler.remove_job(f'snapshot_account_{account_id}')
            logger.info(f"Removed jobs for account {account_id}")
        except Exception as e:
            logger.error(f"Error removing jobs for account {account_id}: {e}")

    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time"""
        if not self.is_running:
            return None

        jobs = self.scheduler.get_jobs()
        if not jobs:
            return None

        return min(job.next_run_time for job in jobs)


# Global scheduler instance
scheduler = MarketScheduler()


def get_scheduler() -> MarketScheduler:
    """Get the global scheduler instance"""
    return scheduler
