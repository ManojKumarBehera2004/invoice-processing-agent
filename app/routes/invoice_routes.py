import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Invoice, InvoiceItem
from app.schemas import (
    InvoiceResponseSchema,
    InvoiceUpdateSchema,
    ValidationResultSchema,
    InvoiceExtractionSchema,
    LineItemSchema
)
from app.services.storage_service import StorageService
from app.services.agent_service import InvoiceProcessingAgent
from app.services.validation_service import ValidationService
from app.config import settings

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

@router.post("/upload", response_model=InvoiceResponseSchema, status_code=status.HTTP_201_CREATED)
async def upload_and_process_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts PDF or image invoice document, saves securely,
    and runs the full AI Document Processing Agent pipeline.
    """
    saved_path, original_filename = await StorageService.validate_and_save_upload(file)
    
    agent = InvoiceProcessingAgent(db=db)
    invoice = await agent.process_document(file_path=saved_path, source_filename=original_filename)
    return invoice

@router.get("", response_model=List[InvoiceResponseSchema])
def list_invoices(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Lists all processed invoices with optional status filtering."""
    query = db.query(Invoice).order_by(Invoice.created_at.desc())
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Invoice.status == status_filter.upper())
    return query.offset(offset).limit(limit).all()

@router.get("/{invoice_id}", response_model=InvoiceResponseSchema)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieves a single invoice by its ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.put("/{invoice_id}", response_model=InvoiceResponseSchema)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdateSchema,
    db: Session = Depends(get_db)
):
    """
    Updates invoice fields and line items, then automatically
    re-runs the validation engine to update validation checks and status.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if payload.vendor_name is not None:
        invoice.vendor_name = payload.vendor_name
    if payload.invoice_number is not None:
        invoice.invoice_number = payload.invoice_number
    if payload.invoice_date is not None:
        invoice.invoice_date = payload.invoice_date
    if payload.currency is not None:
        invoice.currency = payload.currency
    if payload.subtotal is not None:
        invoice.subtotal = payload.subtotal
    if payload.tax is not None:
        invoice.tax = payload.tax
    if payload.total is not None:
        invoice.total = payload.total

    # Update line items if provided
    if payload.line_items is not None:
        # Clear existing items
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()
        for item in payload.line_items:
            new_item = InvoiceItem(
                invoice_id=invoice.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=item.amount
            )
            db.add(new_item)

    # Re-validate with updated values
    current_items = [
        LineItemSchema(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            amount=item.amount
        ) for item in invoice.items
    ]
    if payload.line_items is not None:
        current_items = payload.line_items

    extraction_repr = InvoiceExtractionSchema(
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        currency=invoice.currency,
        line_items=current_items,
        subtotal=invoice.subtotal,
        tax=invoice.tax,
        total=invoice.total,
        confidence=invoice.extraction_confidence or 1.0
    )

    validation_result = ValidationService.validate_invoice(extraction_repr)
    invoice.validation_errors = validation_result.model_dump_json()
    
    # Update high-value flag
    invoice.high_value = bool((invoice.total or 0.0) >= settings.HIGH_VALUE_THRESHOLD)

    # If the user specifically supplied an explicit status, respect it, otherwise apply validation status
    if payload.status:
        invoice.status = payload.status
    else:
        invoice.status = validation_result.status

    db.commit()
    db.refresh(invoice)
    return invoice

@router.post("/{invoice_id}/approve", response_model=InvoiceResponseSchema)
def approve_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Approves an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice.status = "APPROVED"
    db.commit()
    db.refresh(invoice)
    return invoice

@router.post("/{invoice_id}/reject", response_model=InvoiceResponseSchema)
def reject_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Rejects an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice.status = "REJECTED"
    db.commit()
    db.refresh(invoice)
    return invoice

@router.get("/{invoice_id}/validation")
def get_invoice_validation(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieves detailed validation checks for an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.validation_errors:
        try:
            return json.loads(invoice.validation_errors)
        except Exception:
            return {"raw": invoice.validation_errors}
    return {"status": invoice.status, "checks": {}, "errors": [], "warnings": []}

@router.delete("/{invoice_id}", status_code=status.HTTP_200_OK)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Deletes an invoice and its line items."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    db.delete(invoice)
    db.commit()
    return {"message": f"Invoice #{invoice_id} successfully deleted"}

@router.post("/demo/seed", status_code=status.HTTP_201_CREATED)
def seed_demo_invoices(db: Session = Depends(get_db)):
    """
    Populates sample invoices for quick demonstration:
    1. Valid invoice
    2. Invoice with wrong total (calculation mismatch)
    3. High-value invoice (> ₹100,000)
    4. Invoice with missing required fields
    """
    demo_cases = [
        {
            "vendor_name": "Apex Cloud Systems Ltd",
            "invoice_number": "INV-2026-001",
            "invoice_date": "2026-03-15",
            "currency": "INR",
            "subtotal": 45000.0,
            "tax": 8100.0,
            "total": 53100.0,
            "filename": "demo_valid_invoice.pdf",
            "items": [
                ("Cloud Compute Reserved Instance", 2, 15000.0, 30000.0),
                ("Load Balancer & SSL Maintenance", 1, 15000.0, 15000.0)
            ],
            "note": "Fully balanced and valid invoice"
        },
        {
            "vendor_name": "TechFab Hardware Solutions",
            "invoice_number": "INV-2026-002",
            "invoice_date": "2026-03-18",
            "currency": "INR",
            "subtotal": 50000.0,
            "tax": 9000.0,
            "total": 75000.0,  # Intentional calculation mismatch (50000 + 9000 != 75000)
            "filename": "demo_mismatch_invoice.pdf",
            "items": [
                ("Workstation GPU Accelerators", 2, 25000.0, 50000.0)
            ],
            "note": "Calculation mismatch: Total should be 59000, but written as 75000"
        },
        {
            "vendor_name": "Enterprise Quantum Corp",
            "invoice_number": "INV-2026-003",
            "invoice_date": "2026-03-20",
            "currency": "INR",
            "subtotal": 200000.0,
            "tax": 36000.0,
            "total": 236000.0,  # High value (> 100000)
            "filename": "demo_highvalue_invoice.pdf",
            "items": [
                ("AI Supercluster Rack Lease (Monthly)", 1, 200000.0, 200000.0)
            ],
            "note": "High value invoice exceeding threshold of ₹100,000"
        },
        {
            "vendor_name": None,  # Missing vendor name
            "invoice_number": "INV-2026-004",
            "invoice_date": "invalid-date",  # Invalid date
            "currency": "INR",
            "subtotal": 12000.0,
            "tax": 2160.0,
            "total": 14160.0,
            "filename": "demo_missing_fields.pdf",
            "items": [
                ("Office Ergonomic Chairs", 2, 6000.0, 12000.0)
            ],
            "note": "Missing vendor name and invalid date format"
        }
    ]

    created_ids = []
    for case in demo_cases:
        items_schema = [
            LineItemSchema(
                description=desc,
                quantity=q,
                unit_price=p,
                amount=a
            ) for (desc, q, p, a) in case["items"]
        ]
        
        extraction = InvoiceExtractionSchema(
            vendor_name=case["vendor_name"],
            invoice_number=case["invoice_number"],
            invoice_date=case["invoice_date"],
            currency=case["currency"],
            line_items=items_schema,
            subtotal=case["subtotal"],
            tax=case["tax"],
            total=case["total"],
            confidence=0.95 if case["vendor_name"] else 0.60
        )
        
        val_result = ValidationService.validate_invoice(extraction)
        is_high_val = (case["total"] or 0) >= settings.HIGH_VALUE_THRESHOLD

        inv = Invoice(
            vendor_name=case["vendor_name"],
            invoice_number=case["invoice_number"],
            invoice_date=case["invoice_date"],
            currency=case["currency"],
            subtotal=case["subtotal"],
            tax=case["tax"],
            total=case["total"],
            status=val_result.status,
            high_value=is_high_val,
            source_filename=case["filename"],
            file_path=str(settings.UPLOAD_DIR / case["filename"]),
            raw_text=f"Demonstration sample invoice: {case['note']}",
            validation_errors=val_result.model_dump_json(),
            extraction_confidence=val_result.confidence,
            extraction_mode="DEMO_SEED"
        )
        db.add(inv)
        db.flush()

        for (desc, q, p, a) in case["items"]:
            db.add(InvoiceItem(
                invoice_id=inv.id,
                description=desc,
                quantity=q,
                unit_price=p,
                amount=a
            ))
        created_ids.append(inv.id)

    db.commit()
    return {"message": "Demo sample invoices created successfully", "seeded_ids": created_ids}
