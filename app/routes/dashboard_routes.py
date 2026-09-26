from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Invoice
from app.schemas import DashboardStatsSchema, AlertSchema
from app.services.alert_service import AlertService
from typing import List

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsSchema)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Computes aggregated metric counts across the invoice dataset."""
    total = db.query(Invoice).count()
    valid = db.query(Invoice).filter(Invoice.status == "VALID").count()
    flagged = db.query(Invoice).filter(Invoice.status == "FLAGGED").count()
    high_val = db.query(Invoice).filter(Invoice.high_value == True).count()
    review_req = db.query(Invoice).filter(Invoice.status == "REVIEW_REQUIRED").count()
    approved = db.query(Invoice).filter(Invoice.status == "APPROVED").count()

    total_amount_sum = db.query(func.sum(Invoice.total)).scalar() or 0.0

    return DashboardStatsSchema(
        total_invoices=total,
        valid_invoices=valid,
        flagged_invoices=flagged,
        high_value_invoices=high_val,
        review_required_invoices=review_req,
        approved_invoices=approved,
        total_amount=round(float(total_amount_sum), 2),
        currency="INR"
    )

@router.get("/alerts", response_model=List[AlertSchema])
def get_recent_alerts():
    """Retrieves real-time system alerts triggered by processing events."""
    return AlertService.get_recent_alerts(limit=15)
