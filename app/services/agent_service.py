import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Invoice, InvoiceItem
from app.schemas import InvoiceExtractionSchema, ValidationResultSchema
from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService
from app.services.ai_extraction_service import AIExtractionService
from app.services.validation_service import ValidationService
from app.services.alert_service import AlertService
from app.services.sheets_service import GoogleSheetsService

logger = logging.getLogger("AgentOrchestrator")

class InvoiceProcessingAgent:
    """
    Autonomous Document and Invoice Processing Agent.
    Coordinates document ingestion, OCR fallback, AI extraction,
    rule-based validation, alerting, and persistent database storage.
    """
    def __init__(self, db: Session):
        self.db = db
        self.pdf_service = PDFService()
        self.ocr_service = OCRService()
        self.ai_service = AIExtractionService()

    async def process_document(self, file_path: str, source_filename: str) -> Invoice:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        logger.info(f"Agent starting ingestion for: {source_filename} (Format: {ext})")

        # ----------------- Step 1: Text Extraction & OCR -----------------
        raw_text = ""
        is_scanned = False

        if ext == ".pdf":
            try:
                raw_text, is_scanned = self.pdf_service.extract_text(file_path)
                logger.info(f"PDF native text extracted ({len(raw_text)} chars). Is Scanned: {is_scanned}")
                
                # If native text extraction yielded no usable content, render pages & OCR
                if is_scanned or not raw_text.strip():
                    logger.info("PDF has insufficient selectable text. Triggering OCR pipeline...")
                    page_images = self.pdf_service.convert_pdf_to_images(file_path)
                    raw_text = self.ocr_service.extract_text_from_images(page_images)
            except Exception as e:
                logger.error(f"PDF extraction error: {e}")
                raw_text = f"[PDF Processing Error: {str(e)}]"
        elif ext in (".jpg", ".jpeg", ".png"):
            logger.info("Image document detected. Engaging OCR service directly...")
            raw_text = self.ocr_service.extract_text_from_image(file_path)

        if not raw_text.strip():
            raw_text = "[No text could be extracted from document]"

        # ----------------- Step 2: AI Structured Extraction -----------------
        extraction_mode = "AI"
        try:
            extracted_data, extraction_mode = await self.ai_service.extract_invoice_data(
                document_text=raw_text,
                filename=source_filename
            )
            logger.info(f"AI Extraction successful via mode '{extraction_mode}' for invoice '{extracted_data.invoice_number}'")
        except Exception as e:
            logger.error(f"AI extraction failure: {e}")
            AlertService.trigger_alert(
                alert_type="PROCESSING_ERROR",
                message=f"AI extraction failed for file {source_filename}: {str(e)}"
            )
            extracted_data = InvoiceExtractionSchema(
                vendor_name=None,
                invoice_number=None,
                invoice_date=None,
                total=None,
                confidence=0.0
            )
            extraction_mode = "FAILED"

        # ----------------- Step 3: Rule-Based Validation -----------------
        validation: ValidationResultSchema = ValidationService.validate_invoice(extracted_data)
        logger.info(f"Validation completed. Result Status: {validation.status}")

        # ----------------- Step 4: High-Value Detection & Alerts -----------------
        total_amt = extracted_data.total or 0.0
        is_high_value = total_amt >= settings.HIGH_VALUE_THRESHOLD

        if is_high_value:
            AlertService.trigger_alert(
                alert_type="HIGH_VALUE",
                invoice_number=extracted_data.invoice_number or "UNASSIGNED",
                vendor_name=extracted_data.vendor_name or "Unknown",
                amount=total_amt,
                message=f"High-value invoice detected exceeding threshold of ₹{settings.HIGH_VALUE_THRESHOLD:,.2f}"
            )

        if validation.status == "FLAGGED":
            AlertService.trigger_alert(
                alert_type="VALIDATION_FAILURE",
                invoice_number=extracted_data.invoice_number or "UNASSIGNED",
                vendor_name=extracted_data.vendor_name or "Unknown",
                amount=total_amt,
                message=f"Validation errors detected: {'; '.join(validation.errors)}"
            )

        # ----------------- Step 5: Database Persistence -----------------
        db_invoice = Invoice(
            vendor_name=extracted_data.vendor_name,
            invoice_number=extracted_data.invoice_number,
            invoice_date=extracted_data.invoice_date,
            currency=extracted_data.currency or "INR",
            subtotal=extracted_data.subtotal,
            tax=extracted_data.tax,
            total=extracted_data.total,
            status=validation.status,
            high_value=is_high_value,
            source_filename=source_filename,
            file_path=file_path,
            raw_text=raw_text,
            validation_errors=validation.model_dump_json(),
            extraction_confidence=validation.confidence,
            extraction_mode=extraction_mode
        )
        self.db.add(db_invoice)
        self.db.flush()  # obtain db_invoice.id

        # Insert line items
        if extracted_data.line_items:
            for item in extracted_data.line_items:
                db_item = InvoiceItem(
                    invoice_id=db_invoice.id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    amount=item.amount
                )
                self.db.add(db_item)

        self.db.commit()
        self.db.refresh(db_invoice)

        # ----------------- Step 6: Google Sheets Sync (Optional) -----------------
        GoogleSheetsService.append_invoice_row({
            "invoice_number": db_invoice.invoice_number,
            "vendor_name": db_invoice.vendor_name,
            "date": db_invoice.invoice_date,
            "subtotal": db_invoice.subtotal,
            "tax": db_invoice.tax,
            "total": db_invoice.total,
            "status": db_invoice.status,
            "high_value": db_invoice.high_value,
            "created_at": str(db_invoice.created_at)
        })

        logger.info(f"Agent finished processing invoice ID #{db_invoice.id}")
        return db_invoice
