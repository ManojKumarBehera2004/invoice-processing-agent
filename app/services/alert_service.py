import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import List, Optional
from datetime import datetime, timezone
from app.config import settings
from app.schemas import AlertSchema

logger = logging.getLogger("InvoiceAlertService")

# In-memory recent alerts buffer for dashboard viewing
_RECENT_ALERTS: List[AlertSchema] = []

class AlertService:
    @staticmethod
    def get_recent_alerts(limit: int = 20) -> List[AlertSchema]:
        return sorted(_RECENT_ALERTS, key=lambda a: a.timestamp, reverse=True)[:limit]

    @classmethod
    def trigger_alert(
        cls,
        alert_type: str,
        message: str,
        invoice_id: Optional[int] = None,
        invoice_number: Optional[str] = None,
        vendor_name: Optional[str] = None,
        amount: Optional[float] = None
    ) -> AlertSchema:
        alert = AlertSchema(
            alert_type=alert_type,
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            vendor_name=vendor_name,
            amount=amount,
            message=message,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Store in recent alerts
        _RECENT_ALERTS.append(alert)
        if len(_RECENT_ALERTS) > 100:
            _RECENT_ALERTS.pop(0)

        # Log formatted alert clearly to console/logs
        border = "=" * 45
        formatted_log = f"\n{border}\n[ALERT: {alert_type}]\n"
        if invoice_number:
            formatted_log += f"Invoice: {invoice_number}\n"
        if vendor_name:
            formatted_log += f"Vendor:  {vendor_name}\n"
        if amount is not None:
            formatted_log += f"Amount:  ₹{amount:,.2f}\n"
        formatted_log += f"Details: {message}\n{border}"
        
        logger.warning(formatted_log)

        # Send email if SMTP is configured
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
            cls._send_email_alert(alert)

        return alert

    @classmethod
    def _send_email_alert(cls, alert: AlertSchema):
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.ALERT_RECIPIENT_EMAIL
            msg["Subject"] = f"[{alert.alert_type}] Invoice Alert: {alert.invoice_number or 'Unidentified'}"

            body = f"""
            AI Document & Invoice Processing Agent Alert
            --------------------------------------------
            Alert Type: {alert.alert_type}
            Invoice Number: {alert.invoice_number}
            Vendor: {alert.vendor_name}
            Amount: {alert.amount}
            Timestamp: {alert.timestamp}
            
            Message:
            {alert.message}
            """
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Email alert successfully sent to {settings.ALERT_RECIPIENT_EMAIL}")
        except Exception as e:
            logger.error(f"Failed to dispatch email alert: {e}")
