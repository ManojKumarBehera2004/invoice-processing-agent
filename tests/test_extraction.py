import pytest
import pytest_asyncio
from app.schemas import InvoiceExtractionSchema
from app.services.ai_extraction_service import DemoFallbackExtractor

@pytest.mark.asyncio
async def test_demo_fallback_extractor_text():
    sample_text = """
    INVOICE
    Vendor: CloudScale Infrastructure Solutions
    Invoice No: INV-2026-901
    Date: 2026-03-24
    Currency: INR

    Database Managed Cluster    2    20000.00    40000.00
    Virtual Private Gateway     1    10000.00    10000.00

    Subtotal: 50000.00
    Tax: 9000.00
    Total: 59000.00
    """
    extractor = DemoFallbackExtractor()
    extracted, mode = await extractor.extract(sample_text, "sample.pdf")

    assert mode == "DEMO_FALLBACK"
    assert extracted.vendor_name is not None
    assert "CloudScale" in extracted.vendor_name
    assert extracted.invoice_number == "INV-2026-901"
    assert extracted.invoice_date == "2026-03-24"
    assert extracted.currency == "INR"
    assert extracted.subtotal == 50000.0
    assert extracted.tax == 9000.0
    assert extracted.total == 59000.0
    assert len(extracted.line_items) >= 1

def test_pydantic_schema_strictness():
    # Verify strict serialization of empty/missing values to null
    empty_schema = InvoiceExtractionSchema()
    dumped = empty_schema.model_dump()
    assert dumped["vendor_name"] is None
    assert dumped["invoice_number"] is None
    assert dumped["total"] is None
    assert dumped["line_items"] == []
