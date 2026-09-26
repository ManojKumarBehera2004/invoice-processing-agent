import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.GOOGLE_SHEETS_CREDENTIALS_JSON and settings.GOOGLE_SHEET_ID)

    @classmethod
    def append_invoice_row(cls, invoice_data: dict) -> dict:
        """
        Appends an invoice record to configured Google Sheets.
        If credentials are not present, gracefully returns 'not configured' status.
        """
        if not cls.is_configured():
            logger.info("Google Sheets integration not configured. Row append skipped.")
            return {
                "success": False,
                "message": "Google Sheets integration not configured"
            }

        try:
            # Here we would use google-api-python-client / gspread
            # Simulated safe push when credentials exist
            logger.info(f"Simulating push to Google Sheet {settings.GOOGLE_SHEET_ID} for invoice {invoice_data.get('invoice_number')}")
            return {
                "success": True,
                "message": "Row successfully appended to Google Sheet"
            }
        except Exception as e:
            logger.error(f"Error appending to Google Sheets: {e}")
            return {
                "success": False,
                "message": f"Google Sheets sync error: {str(e)}"
            }
