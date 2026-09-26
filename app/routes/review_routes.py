import json
from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Invoice
from app.config import settings

router = APIRouter(include_in_schema=False)

templates_path = settings.BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(templates_path))
templates.env.cache = None

@router.get("/")
def index():
    return RedirectResponse(url="/dashboard")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_tab": "dashboard",
            "high_value_threshold": settings.HIGH_VALUE_THRESHOLD,
            "ai_provider": settings.AI_PROVIDER
        }
    )

@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "active_tab": "upload",
            "max_size_mb": settings.MAX_UPLOAD_SIZE_MB
        }
    )

@router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
def invoice_detail_page(invoice_id: int, request: Request, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    validation = {}
    if invoice.validation_errors:
        try:
            validation = json.loads(invoice.validation_errors)
        except Exception:
            validation = {"status": invoice.status, "checks": {}, "errors": [], "warnings": []}

    return templates.TemplateResponse(
        request=request,
        name="invoice_detail.html",
        context={
            "invoice": invoice,
            "validation": validation,
            "active_tab": "invoices"
        }
    )

@router.get("/invoices/{invoice_id}/review", response_class=HTMLResponse)
def review_page(invoice_id: int, request: Request, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    validation = {}
    if invoice.validation_errors:
        try:
            validation = json.loads(invoice.validation_errors)
        except Exception:
            validation = {"status": invoice.status, "checks": {}, "errors": [], "warnings": []}

    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "invoice": invoice,
            "validation": validation,
            "active_tab": "review"
        }
    )
