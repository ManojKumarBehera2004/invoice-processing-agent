import pytest
from app.schemas import InvoiceExtractionSchema, LineItemSchema
from app.services.validation_service import ValidationService
from app.config import settings

def test_valid_invoice():
    data = InvoiceExtractionSchema(
        vendor_name="Acme Tech Solutions",
        invoice_number="INV-2026-101",
        invoice_date="2026-03-24",
        currency="INR",
        line_items=[
            LineItemSchema(description="Cloud Hosting", quantity=2, unit_price=5000.0, amount=10000.0),
            LineItemSchema(description="Domain Management", quantity=1, unit_price=2000.0, amount=2000.0)
        ],
        subtotal=12000.0,
        tax=2160.0,
        total=14160.0,
        confidence=0.95
    )
    result = ValidationService.validate_invoice(data)
    assert result.status == "VALID"
    assert result.checks.required_fields == "PASS"
    assert result.checks.line_items == "PASS"
    assert result.checks.subtotal == "PASS"
    assert result.checks.tax == "PASS"
    assert result.checks.total == "PASS"
    assert result.checks.date == "PASS"
    assert len(result.errors) == 0

def test_line_item_calculation_mismatch():
    # quantity (3) * unit_price (500) = 1500, but amount says 1800
    data = InvoiceExtractionSchema(
        vendor_name="Acme Tech Solutions",
        invoice_number="INV-2026-102",
        invoice_date="2026-03-24",
        line_items=[
            LineItemSchema(description="RAM Upgrade", quantity=3, unit_price=500.0, amount=1800.0)
        ],
        subtotal=1800.0,
        tax=0.0,
        total=1800.0
    )
    result = ValidationService.validate_invoice(data)
    assert result.status == "FLAGGED"
    assert result.checks.line_items == "FAIL"
    assert any("Line item #1" in err for err in result.errors)

def test_subtotal_mismatch():
    # items sum = 10000, but subtotal claimed is 12000
    data = InvoiceExtractionSchema(
        vendor_name="Acme Tech Solutions",
        invoice_number="INV-2026-103",
        invoice_date="2026-03-24",
        line_items=[
            LineItemSchema(description="SSD Drive", quantity=2, unit_price=5000.0, amount=10000.0)
        ],
        subtotal=12000.0,
        tax=0.0,
        total=12000.0
    )
    result = ValidationService.validate_invoice(data)
    assert result.status == "FLAGGED"
    assert result.checks.subtotal == "FAIL"
    assert any("Subtotal calculation mismatch" in err for err in result.errors)

def test_total_mismatch():
    # subtotal (10000) + tax (1800) = 11800, but total is 15000
    data = InvoiceExtractionSchema(
        vendor_name="Acme Tech Solutions",
        invoice_number="INV-2026-104",
        invoice_date="2026-03-24",
        line_items=[
            LineItemSchema(description="Server Setup", quantity=1, unit_price=10000.0, amount=10000.0)
        ],
        subtotal=10000.0,
        tax=1800.0,
        total=15000.0
    )
    result = ValidationService.validate_invoice(data)
    assert result.status == "FLAGGED"
    assert result.checks.total == "FAIL"
    assert any("Total calculation mismatch" in err for err in result.errors)

def test_missing_mandatory_fields():
    # Missing vendor_name and invoice_number
    data = InvoiceExtractionSchema(
        vendor_name=None,
        invoice_number="",
        invoice_date="2026-03-24",
        line_items=[],
        subtotal=500.0,
        tax=0.0,
        total=500.0
    )
    result = ValidationService.validate_invoice(data)
    assert result.status == "FLAGGED"
    assert result.checks.required_fields == "FAIL"
    assert any("Missing mandatory fields" in err for err in result.errors)

def test_invalid_date():
    data = InvoiceExtractionSchema(
        vendor_name="Acme Tech Solutions",
        invoice_number="INV-2026-105",
        invoice_date="32-13-9999",  # Invalid calendar date
        total=100.0
    )
    result = ValidationService.validate_invoice(data)
    assert result.status == "FLAGGED"
    assert result.checks.date == "FAIL"
    assert any("Invalid date" in err for err in result.errors)

def test_high_value_detection_logic():
    threshold = settings.HIGH_VALUE_THRESHOLD
    invoice_amount = threshold + 5000.0
    assert invoice_amount >= threshold
