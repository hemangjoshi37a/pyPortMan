"""
Auto Login Manager for pyPortMan Backend
Automated Zerodha login using Playwright with TOTP support
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page
from sqlalchemy.orm import Session
import pyotp

from models import Account
from encryption import get_encryption_manager

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


class AutoLoginManager:
    """Manager for automated Zerodha login and token refresh"""

    def __init__(self, db: Session):
        self.db = db
        self.encryption = get_encryption_manager()

    def get_totp(self, totp_secret: str) -> str:
        """
        Generate TOTP code from secret

        Args:
            totp_secret: TOTP secret (encrypted or plain)

        Returns:
            6-digit TOTP code
        """
        try:
            # Try to decrypt if it's encrypted
            try:
                secret = self.encryption.decrypt(totp_secret)
            except Exception:
                # Already plain text
                secret = totp_secret

            totp = pyotp.TOTP(secret)
            return totp.now()
        except Exception as e:
            logger.error(f"Error generating TOTP: {e}")
            raise ValueError(f"Failed to generate TOTP: {e}")

    async def auto_login(self, account: Account) -> Optional[str]:
        """
        Perform automated login for a Zerodha account

        Args:
            account: Account object with credentials

        Returns:
            Access token if successful, None otherwise
        """
        if not account.auto_login_enabled:
            logger.warning(f"Auto-login disabled for account {account.id}")
            return None

        if not account.password or not account.totp_secret:
            logger.error(f"Missing credentials for auto-login on account {account.id}")
            return None

        try:
            # Decrypt credentials
            password = self.encryption.decrypt(account.password)
            totp_secret = account.totp_secret

            logger.info(f"Starting auto-login for account {account.account_id}")

            async with async_playwright() as p:
                # Launch browser (headless mode)
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                try:
                    # Navigate to Zerodha login
                    await page.goto("https://kite.zerodha.com", wait_until="networkidle")
                    logger.info("Navigated to Zerodha login page")

                    # Wait for login form
                    await page.wait_for_selector('input[type="text"]', timeout=10000)

                    # Enter user ID
                    await page.fill('input[type="text"]', account.account_id)
                    logger.info("Entered user ID")

                    # Enter password
                    await page.fill('input[type="password"]', password)
                    logger.info("Entered password")

                    # Click login button
                    await page.click('button[type="submit"]')
                    logger.info("Clicked login button")

                    # Wait for TOTP page
                    await page.wait_for_selector('input[type="text"]', timeout=15000)
                    logger.info("Waiting for TOTP input")

                    # Generate and enter TOTP
                    totp_code = self.get_totp(totp_secret)
                    logger.info(f"Generated TOTP: {totp_code}")

                    await page.fill('input[type="text"]', totp_code)
                    logger.info("Entered TOTP")

                    # Submit TOTP
                    await page.click('button[type="submit"]')
                    logger.info("Submitted TOTP")

                    # Wait for redirect and extract request_token from URL
                    await page.wait_for_url("**/dashboard**", timeout=30000)
                    logger.info("Login successful, redirected to dashboard")

                    # Get current URL which should contain request_token
                    current_url = page.url
                    logger.info(f"Current URL: {current_url}")

                    # Extract request_token from URL
                    # URL format: https://kite.zerodha.com/dashboard?request_token=xxx
                    request_token = None
                    if "request_token=" in current_url:
                        request_token = current_url.split("request_token=")[1].split("&")[0]
                        logger.info(f"Extracted request_token: {request_token}")

                    await browser.close()

                    if request_token:
                        # Generate access token using KiteConnect
                        access_token = await self._generate_access_token(account, request_token)
                        return access_token
                    else:
                        logger.error("Could not extract request_token from URL")
                        return None

                except Exception as e:
                    logger.error(f"Error during login process: {e}")
                    await browser.close()
                    return None

        except Exception as e:
            logger.error(f"Auto-login failed for account {account.id}: {e}")
            return None

    async def _generate_access_token(self, account: Account, request_token: str) -> Optional[str]:
        """
        Generate access token from request token

        Args:
            account: Account object
            request_token: Request token from Zerodha

        Returns:
            Access token if successful
        """
        try:
            from kiteconnect import KiteConnect

            kite = KiteConnect(api_key=account.api_key)
            data = kite.generate_session(request_token, account.api_secret)

            access_token = data.get("access_token")
            if access_token:
                # Update account with new access token
                account.access_token = access_token
                account.request_token = request_token
                account.last_login_at = datetime.utcnow()
                account.last_token_refresh = datetime.utcnow()
                # Token expires at 6 AM IST next day
                account.token_expires_at = datetime.utcnow().replace(hour=0, minute=30) + timedelta(days=1)

                self.db.commit()
                logger.info(f"Access token generated and saved for account {account.id}")
                return access_token
            else:
                logger.error("No access_token in response")
                return None

        except Exception as e:
            logger.error(f"Error generating access token: {e}")
            self.db.rollback()
            return None

    async def refresh_all_accounts(self) -> Dict[str, Any]:
        """
        Refresh tokens for all accounts with auto-login enabled

        Returns:
            Dict with results for each account
        """
        accounts = self.db.query(Account).filter(
            Account.is_active == True,
            Account.auto_login_enabled == True
        ).all()

        results = {
            "total": len(accounts),
            "success": 0,
            "failed": 0,
            "accounts": []
        }

        for account in accounts:
            try:
                logger.info(f"Refreshing token for account {account.account_id}")
                access_token = await self.auto_login(account)

                if access_token:
                    results["success"] += 1
                    results["accounts"].append({
                        "account_id": account.id,
                        "account_name": account.name,
                        "status": "success",
                        "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None
                    })
                else:
                    results["failed"] += 1
                    results["accounts"].append({
                        "account_id": account.id,
                        "account_name": account.name,
                        "status": "failed",
                        "error": "Failed to generate access token"
                    })

            except Exception as e:
                results["failed"] += 1
                results["accounts"].append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"Error refreshing account {account.id}: {e}")

        logger.info(f"Token refresh complete: {results['success']} success, {results['failed']} failed")
        return results

    async def refresh_account(self, account_id: int) -> Optional[str]:
        """
        Refresh token for a specific account

        Args:
            account_id: Account ID

        Returns:
            Access token if successful
        """
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            logger.error(f"Account {account_id} not found")
            return None

        return await self.auto_login(account)

    def save_credentials(self, account_id: int, password: str, totp_secret: str) -> bool:
        """
        Save encrypted credentials for an account

        Args:
            account_id: Account ID
            password: Zerodha password
            totp_secret: TOTP secret

        Returns:
            True if successful
        """
        try:
            account = self.db.query(Account).filter(Account.id == account_id).first()
            if not account:
                logger.error(f"Account {account_id} not found")
                return False

            # Encrypt and save credentials
            account.password = self.encryption.encrypt(password)
            account.totp_secret = self.encryption.encrypt(totp_secret)
            account.auto_login_enabled = True

            self.db.commit()
            logger.info(f"Credentials saved for account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            self.db.rollback()
            return False

    def remove_credentials(self, account_id: int) -> bool:
        """
        Remove credentials and disable auto-login for an account

        Args:
            account_id: Account ID

        Returns:
            True if successful
        """
        try:
            account = self.db.query(Account).filter(Account.id == account_id).first()
            if not account:
                logger.error(f"Account {account_id} not found")
                return False

            account.password = None
            account.totp_secret = None
            account.auto_login_enabled = False

            self.db.commit()
            logger.info(f"Credentials removed for account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing credentials: {e}")
            self.db.rollback()
            return False

    def get_auto_login_status(self, account_id: int) -> Dict[str, Any]:
        """
        Get auto-login status for an account

        Args:
            account_id: Account ID

        Returns:
            Dict with status information
        """
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return {"error": "Account not found"}

        return {
            "account_id": account.id,
            "account_name": account.name,
            "auto_login_enabled": account.auto_login_enabled,
            "has_credentials": bool(account.password and account.totp_secret),
            "last_token_refresh": account.last_token_refresh.isoformat() if account.last_token_refresh else None,
            "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
            "token_expired": account.token_expires_at and datetime.utcnow() > account.token_expires_at
        }


# Convenience function for sync code
def run_async(coro):
    """Run async function from sync code"""
    return asyncio.run(coro)


if __name__ == "__main__":
    # Test auto-login
    from database import SessionLocal

    db = SessionLocal()
    manager = AutoLoginManager(db)

    # Test TOTP generation
    test_secret = "JBSWY3DPEHPK3PXP"  # Example secret
    totp_code = manager.get_totp(test_secret)
    print(f"TOTP Code: {totp_code}")

    db.close()
