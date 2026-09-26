from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_name = Column(String(255), nullable=True)
    invoice_number = Column(String(100), nullable=True, index=True)
    invoice_date = Column(String(50), nullable=True)
    currency = Column(String(10), default="INR", nullable=True)
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    status = Column(String(50), default="PENDING", index=True)  # VALID, FLAGGED, REVIEW_REQUIRED, APPROVED, REJECTED, PROCESSING_ERROR
    high_value = Column(Boolean, default=False, index=True)
    source_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    raw_text = Column(Text, nullable=True)
    validation_errors = Column(Text, nullable=True)  # JSON-encoded validation result
    extraction_confidence = Column(Float, default=1.0)
    extraction_mode = Column(String(50), default="AI")  # "AI" or "DEMO_FALLBACK"
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", lazy="joined")

    def __repr__(self):
        return f"<Invoice id={self.id} number={self.invoice_number} vendor={self.vendor_name} total={self.total} status={self.status}>"


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")

    def __repr__(self):
        return f"<InvoiceItem id={self.id} desc={self.description} qty={self.quantity} unit_price={self.unit_price} amount={self.amount}>"
