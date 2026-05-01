"""
Email Alerts Manager for pyPortMan
Send email alerts for critical events (large losses, margin calls)
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, EmailConfig, AlertHistory

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


class EmailAlertsManager:
    """Manager for email alerts"""

    def __init__(self, db: Session):
        self.db = db

    def get_config(self) -> Optional[EmailConfig]:
        """Get email configuration"""
        return self.db.query(EmailConfig).first()

    def save_config(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        to_emails: str,
        gtt_alerts_enabled: bool = True,
        loss_alerts_enabled: bool = True,
        margin_call_alerts_enabled: bool = True,
        daily_summary_enabled: bool = True,
        loss_threshold_pct: float = 5.0
    ) -> EmailConfig:
        """Save email configuration"""
        config = self.get_config()

        if not config:
            config = EmailConfig(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                from_email=from_email,
                to_emails=to_emails,
                gtt_alerts_enabled=gtt_alerts_enabled,
                loss_alerts_enabled=loss_alerts_enabled,
                margin_call_alerts_enabled=margin_call_alerts_enabled,
                daily_summary_enabled=daily_summary_enabled,
                loss_threshold_pct=loss_threshold_pct
            )
            self.db.add(config)
        else:
            config.smtp_server = smtp_server
            config.smtp_port = smtp_port
            config.smtp_username = smtp_username
            config.smtp_password = smtp_password
            config.from_email = from_email
            config.to_emails = to_emails
            config.gtt_alerts_enabled = gtt_alerts_enabled
            config.loss_alerts_enabled = loss_alerts_enabled
            config.margin_call_alerts_enabled = margin_call_alerts_enabled
            config.daily_summary_enabled = daily_summary_enabled
            config.loss_threshold_pct = loss_threshold_pct
            config.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(config)

        logger.info("Email configuration saved")
        return config

    def send_email(
        self,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send an email
        """
        config = self.get_config()

        if not config:
            logger.error("Email configuration not found")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config.from_email
            msg['To'] = config.to_emails

            # Add plain text version
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML version if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Connect to SMTP server
            with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
                server.starttls()
                server.login(config.smtp_username, config.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_loss_alert(
        self,
        account_id: int,
        account_name: str,
        stock: str,
        loss_pct: float,
        loss_amount: float
    ) -> bool:
        """Send alert when loss threshold is crossed"""
        config = self.get_config()

        if not config or not config.loss_alerts_enabled:
            return False

        subject = f"⚠️ Loss Alert - {stock} ({account_name})"

        body = f"""
pyPortMan Loss Alert
====================

Account: {account_name}
Stock: {stock}
Loss: {loss_pct:.2f}% (₹{loss_amount:.2f})
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

This is an automated alert from pyPortMan.
Please review your position and take appropriate action.
"""

        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .alert {{ background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; }}
        .header {{ color: #f44336; font-size: 18px; font-weight: bold; }}
        .data {{ margin: 10px 0; }}
        .label {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="alert">
        <div class="header">⚠️ Loss Alert</div>
        <div class="data"><span class="label">Account:</span> {account_name}</div>
        <div class="data"><span class="label">Stock:</span> {stock}</div>
        <div class="data"><span class="label">Loss:</span> {loss_pct:.2f}% (₹{loss_amount:.2f})</div>
        <div class="data"><span class="label">Time:</span> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</div>
        <p style="margin-top: 15px;">This is an automated alert from pyPortMan.</p>
    </div>
</body>
</html>
"""

        success = self.send_email(subject, body, html_body)

        # Log alert history
        self._log_alert("EMAIL_LOSS_ALERT", body, success)

        return success

    def send_margin_call_alert(
        self,
        account_id: int,
        account_name: str,
        margin_used: float,
        margin_available: float,
        total_margin: float
    ) -> bool:
        """Send alert when margin is running low"""
        config = self.get_config()

        if not config or not config.margin_call_alerts_enabled:
            return False

        subject = f"🚨 Margin Call Alert - {account_name}"

        body = f"""
pyPortMan Margin Call Alert
===========================

Account: {account_name}
Margin Used: ₹{margin_used:.2f}
Margin Available: ₹{margin_available:.2f}
Total Margin: ₹{total_margin:.2f}
Margin Usage: {(margin_used / total_margin * 100):.2f}%
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

WARNING: Your margin usage is high. Please consider reducing positions or adding funds.

This is an automated alert from pyPortMan.
"""

        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .alert {{ background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; }}
        .header {{ color: #ff9800; font-size: 18px; font-weight: bold; }}
        .data {{ margin: 10px 0; }}
        .label {{ font-weight: bold; }}
        .warning {{ color: #ff9800; font-weight: bold; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="alert">
        <div class="header">🚨 Margin Call Alert</div>
        <div class="data"><span class="label">Account:</span> {account_name}</div>
        <div class="data"><span class="label">Margin Used:</span> ₹{margin_used:.2f}</div>
        <div class="data"><span class="label">Margin Available:</span> ₹{margin_available:.2f}</div>
        <div class="data"><span class="label">Total Margin:</span> ₹{total_margin:.2f}</div>
        <div class="data"><span class="label">Margin Usage:</span> {(margin_used / total_margin * 100):.2f}%</div>
        <div class="data"><span class="label">Time:</span> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</div>
        <p class="warning">WARNING: Your margin usage is high. Please consider reducing positions or adding funds.</p>
        <p style="margin-top: 15px;">This is an automated alert from pyPortMan.</p>
    </div>
</body>
</html>
"""

        success = self.send_email(subject, body, html_body)

        # Log alert history
        self._log_alert("EMAIL_MARGIN_CALL", body, success)

        return success

    def send_daily_summary(
        self,
        account_id: int,
        account_name: str,
        total_pnl: float,
        pnl_pct: float,
        holdings_count: int
    ) -> bool:
        """Send daily portfolio summary"""
        config = self.get_config()

        if not config or not config.daily_summary_enabled:
            return False

        emoji = "📈" if total_pnl >= 0 else "📉"
        subject = f"{emoji} Daily Portfolio Summary - {account_name}"

        body = f"""
pyPortMan Daily Summary
======================

Account: {account_name}
Total P&L: ₹{total_pnl:.2f} ({pnl_pct:+.2f}%)
Holdings: {holdings_count}
Date: {datetime.utcnow().strftime('%Y-%m-%d')}

This is an automated daily summary from pyPortMan.
"""

        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .summary {{ background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; }}
        .header {{ color: #2196f3; font-size: 18px; font-weight: bold; }}
        .data {{ margin: 10px 0; }}
        .label {{ font-weight: bold; }}
        .pnl {{ color: {'green' if total_pnl >= 0 else 'red'}; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="summary">
        <div class="header">📊 Daily Portfolio Summary</div>
        <div class="data"><span class="label">Account:</span> {account_name}</div>
        <div class="data"><span class="label">Total P&L:</span> <span class="pnl">₹{total_pnl:.2f} ({pnl_pct:+.2f}%)</span></div>
        <div class="data"><span class="label">Holdings:</span> {holdings_count}</div>
        <div class="data"><span class="label">Date:</span> {datetime.utcnow().strftime('%Y-%m-%d')}</div>
        <p style="margin-top: 15px;">This is an automated daily summary from pyPortMan.</p>
    </div>
</body>
</html>
"""

        success = self.send_email(subject, body, html_body)

        # Log alert history
        self._log_alert("EMAIL_DAILY_SUMMARY", body, success)

        return success

    def send_gtt_alert(
        self,
        account_id: int,
        account_name: str,
        stock: str,
        trigger_price: float,
        qty: int
    ) -> bool:
        """Send alert when GTT order is triggered"""
        config = self.get_config()

        if not config or not config.gtt_alerts_enabled:
            return False

        subject = f"🎯 GTT Triggered - {stock} ({account_name})"

        body = f"""
pyPortMan GTT Alert
==================

Account: {account_name}
Stock: {stock}
Trigger Price: ₹{trigger_price:.2f}
Quantity: {qty}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

This is an automated alert from pyPortMan.
"""

        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .alert {{ background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; }}
        .header {{ color: #4caf50; font-size: 18px; font-weight: bold; }}
        .data {{ margin: 10px 0; }}
        .label {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="alert">
        <div class="header">🎯 GTT Triggered</div>
        <div class="data"><span class="label">Account:</span> {account_name}</div>
        <div class="data"><span class="label">Stock:</span> {stock}</div>
        <div class="data"><span class="label">Trigger Price:</span> ₹{trigger_price:.2f}</div>
        <div class="data"><span class="label">Quantity:</span> {qty}</div>
        <div class="data"><span class="label">Time:</span> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</div>
        <p style="margin-top: 15px;">This is an automated alert from pyPortMan.</p>
    </div>
</body>
</html>
"""

        success = self.send_email(subject, body, html_body)

        # Log alert history
        self._log_alert("EMAIL_GTT_ALERT", body, success)

        return success

    def _log_alert(self, alert_type: str, message: str, success: bool) -> None:
        """Log alert to history"""
        alert = AlertHistory(
            alert_type=alert_type,
            message=message,
            sent_at=datetime.utcnow(),
            success=success
        )
        self.db.add(alert)
        self.db.commit()

    def test_connection(self) -> Dict[str, Any]:
        """Test email connection"""
        config = self.get_config()

        if not config:
            return {
                "success": False,
                "error": "Email configuration not found"
            }

        subject = "✅ pyPortMan Test Email"
        body = f"""
pyPortMan Test Email
====================

This is a test email from pyPortMan.

Your email alerts are working correctly!

Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
"""

        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .test {{ background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; }}
        .header {{ color: #4caf50; font-size: 18px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="test">
        <div class="header">✅ Test Email</div>
        <p>This is a test email from pyPortMan.</p>
        <p>Your email alerts are working correctly!</p>
        <p>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""

        success = self.send_email(subject, body, html_body)

        return {
            "success": success,
            "message": "Test email sent successfully!" if success else "Failed to send test email"
        }
