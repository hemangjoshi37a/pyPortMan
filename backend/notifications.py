"""
Notifications Module for pyPortMan
Implements email, SMS, and webhook notification support
"""

import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models import AlertHistory

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


class EmailNotifier:
    """Email notification handler"""

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_username: str = "",
        smtp_password: str = "",
        from_email: str = ""
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Send an email notification

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            html: Whether body is HTML (default False)

        Returns: True if successful
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html' if html else 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_alert_email(
        self,
        to_email: str,
        alert_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an alert email with formatted content

        Args:
            to_email: Recipient email address
            alert_type: Type of alert
            message: Alert message
            data: Optional additional data

        Returns: True if successful
        """
        subject = f"pyPortMan Alert: {alert_type}"

        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563EB; color: white; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f5f5f5; }}
                .alert-type {{ font-size: 18px; font-weight: bold; color: #2563EB; }}
                .message {{ margin: 15px 0; }}
                .data {{ background-color: white; padding: 15px; border-radius: 5px; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>pyPortMan Alert</h2>
                </div>
                <div class="content">
                    <div class="alert-type">{alert_type}</div>
                    <div class="message">{message}</div>
                    {self._format_data_html(data) if data else ''}
                </div>
                <div class="footer">
                    <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>This is an automated message from pyPortMan</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, html_body, html=True)

    def _format_data_html(self, data: Dict[str, Any]) -> str:
        """Format data as HTML table"""
        if not data:
            return ""

        rows = ""
        for key, value in data.items():
            rows += f"<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>"

        return f'<div class="data"><table>{rows}</table></div>'


class SMSNotifier:
    """SMS notification handler (using Twilio or similar service)"""

    def __init__(
        self,
        service: str = "twilio",
        account_sid: str = "",
        auth_token: str = "",
        from_number: str = ""
    ):
        self.service = service
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def send_sms(
        self,
        to_number: str,
        message: str
    ) -> bool:
        """
        Send an SMS notification

        Args:
            to_number: Recipient phone number
            message: SMS message content

        Returns: True if successful
        """
        try:
            if self.service == "twilio":
                return self._send_twilio_sms(to_number, message)
            else:
                logger.error(f"Unsupported SMS service: {self.service}")
                return False
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False

    def _send_twilio_sms(self, to_number: str, message: str) -> bool:
        """Send SMS using Twilio API"""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            data = {
                "From": self.from_number,
                "To": to_number,
                "Body": message
            }

            response = requests.post(
                url,
                data=data,
                auth=(self.account_sid, self.auth_token)
            )

            if response.status_code == 201:
                logger.info(f"SMS sent to {to_number}")
                return True
            else:
                logger.error(f"Twilio error: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Twilio SMS: {e}")
            return False

    def send_alert_sms(
        self,
        to_number: str,
        alert_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an alert SMS with formatted content

        Args:
            to_number: Recipient phone number
            alert_type: Type of alert
            message: Alert message
            data: Optional additional data

        Returns: True if successful
        """
        sms_message = f"[pyPortMan] {alert_type}\n{message}"

        if data:
            sms_message += "\n\nDetails:\n"
            for key, value in data.items():
                sms_message += f"{key}: {value}\n"

        return self.send_sms(to_number, sms_message)


class WebhookNotifier:
    """Webhook notification handler"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a webhook notification

        Args:
            url: Webhook URL
            payload: JSON payload to send
            headers: Optional HTTP headers

        Returns: True if successful
        """
        try:
            default_headers = {
                "Content-Type": "application/json",
                "User-Agent": "pyPortMan/1.0"
            }

            if headers:
                default_headers.update(headers)

            response = requests.post(
                url,
                json=payload,
                headers=default_headers,
                timeout=self.timeout
            )

            if response.status_code in [200, 201, 202, 204]:
                logger.info(f"Webhook sent to {url}")
                return True
            else:
                logger.error(f"Webhook error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False

    def send_alert_webhook(
        self,
        url: str,
        alert_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an alert webhook with formatted payload

        Args:
            url: Webhook URL
            alert_type: Type of alert
            message: Alert message
            data: Optional additional data

        Returns: True if successful
        """
        payload = {
            "alert_type": alert_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "pyPortMan"
        }

        if data:
            payload["data"] = data

        return self.send_webhook(url, payload)


class NotificationsManager:
    """Manager for all notification types"""

    def __init__(self, db: Session):
        self.db = db
        self.email_notifier = None
        self.sms_notifier = None
        self.webhook_notifier = WebhookNotifier()

    def configure_email(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str
    ):
        """Configure email notifications"""
        self.email_notifier = EmailNotifier(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            from_email=from_email
        )

    def configure_sms(
        self,
        service: str,
        account_sid: str,
        auth_token: str,
        from_number: str
    ):
        """Configure SMS notifications"""
        self.sms_notifier = SMSNotifier(
            service=service,
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number
        )

    def send_notification(
        self,
        notification_type: str,
        recipients: List[str],
        alert_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send notification via specified type(s)

        Args:
            notification_type: "email", "sms", "webhook", or "all"
            recipients: List of recipient addresses/numbers/URLs
            alert_type: Type of alert
            message: Alert message
            data: Optional additional data

        Returns: {success: bool, results: {...}}
        """
        results = {}
        success_count = 0

        if notification_type in ["email", "all"] and self.email_notifier:
            for recipient in recipients:
                result = self.email_notifier.send_alert_email(
                    recipient, alert_type, message, data
                )
                results[f"email_{recipient}"] = result
                if result:
                    success_count += 1

        if notification_type in ["sms", "all"] and self.sms_notifier:
            for recipient in recipients:
                result = self.sms_notifier.send_alert_sms(
                    recipient, alert_type, message, data
                )
                results[f"sms_{recipient}"] = result
                if result:
                    success_count += 1

        if notification_type in ["webhook", "all"]:
            for recipient in recipients:
                result = self.webhook_notifier.send_alert_webhook(
                    recipient, alert_type, message, data
                )
                results[f"webhook_{recipient}"] = result
                if result:
                    success_count += 1

        total = len(results)
        success = success_count == total

        # Log to alert history
        self._log_alert_history(
            notification_type,
            alert_type,
            message,
            success,
            results
        )

        return {
            "success": success,
            "success_count": success_count,
            "total": total,
            "results": results
        }

    def _log_alert_history(
        self,
        notification_type: str,
        alert_type: str,
        message: str,
        success: bool,
        results: Dict[str, Any]
    ):
        """Log alert to history"""
        try:
            history = AlertHistory(
                alert_type=f"{notification_type}_{alert_type}",
                message=message,
                sent_at=datetime.utcnow(),
                success=success
            )
            self.db.add(history)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging alert history: {e}")

    def test_email(self, to_email: str) -> Dict[str, Any]:
        """Test email notification"""
        if not self.email_notifier:
            return {"success": False, "error": "Email not configured"}

        return {
            "success": self.email_notifier.send_email(
                to_email,
                "pyPortMan Test Email",
                "This is a test email from pyPortMan. Your email notifications are working!"
            )
        }

    def test_sms(self, to_number: str) -> Dict[str, Any]:
        """Test SMS notification"""
        if not self.sms_notifier:
            return {"success": False, "error": "SMS not configured"}

        return {
            "success": self.sms_notifier.send_sms(
                to_number,
                "pyPortMan Test SMS - Your SMS notifications are working!"
            )
        }

    def test_webhook(self, url: str) -> Dict[str, Any]:
        """Test webhook notification"""
        return {
            "success": self.webhook_notifier.send_webhook(
                url,
                {
                    "test": True,
                    "message": "pyPortMan test webhook",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        }
