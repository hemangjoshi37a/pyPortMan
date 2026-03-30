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
