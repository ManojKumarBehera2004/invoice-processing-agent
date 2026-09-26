from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# ----------------- Line Item Schemas -----------------

class LineItemSchema(BaseModel):
    description: str = Field(..., description="Line item description")
    quantity: float = Field(default=1.0, description="Quantity of item")
    unit_price: float = Field(default=0.0, description="Unit price of item")
    amount: float = Field(default=0.0, description="Total amount for this line item")

class LineItemResponse(LineItemSchema):
    id: int
    invoice_id: int
    model_config = ConfigDict(from_attributes=True)

# ----------------- AI Extraction Schema -----------------

class InvoiceExtractionSchema(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None  # Expected normalized YYYY-MM-DD
    currency: Optional[str] = "INR"
    line_items: List[LineItemSchema] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    confidence: Optional[float] = Field(default=1.0, description="Confidence score 0.0 to 1.0")

# ----------------- Validation Schemas -----------------

class ValidationChecks(BaseModel):
    required_fields: str = "PASS"  # PASS or FAIL
    line_items: str = "PASS"
    subtotal: str = "PASS"
    tax: str = "PASS"
    total: str = "PASS"
    date: str = "PASS"

class ValidationResultSchema(BaseModel):
    status: str = "VALID"  # VALID, FLAGGED, REVIEW_REQUIRED, PROCESSING_ERROR
    checks: ValidationChecks
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence: float = 1.0

# ----------------- Invoice CRUD / Response Schemas -----------------

class InvoiceUpdateSchema(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    status: Optional[str] = None
    line_items: Optional[List[LineItemSchema]] = None

class InvoiceResponseSchema(BaseModel):
    id: int
    vendor_name: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    currency: Optional[str]
    subtotal: Optional[float]
    tax: Optional[float]
    total: Optional[float]
    status: str
    high_value: bool
    source_filename: str
    file_path: str
    raw_text: Optional[str]
    validation_errors: Optional[str]
    extraction_confidence: Optional[float]
    extraction_mode: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: List[LineItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ----------------- Dashboard Statistics -----------------

class DashboardStatsSchema(BaseModel):
    total_invoices: int
    valid_invoices: int
    flagged_invoices: int
    high_value_invoices: int
    review_required_invoices: int
    approved_invoices: int
    total_amount: float
    currency: str = "INR"

# ----------------- Alerts -----------------

class AlertSchema(BaseModel):
    alert_type: str  # HIGH_VALUE, VALIDATION_FAILURE, MISSING_FIELDS, PROCESSING_ERROR
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
