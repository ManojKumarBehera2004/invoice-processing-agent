import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Invoice

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup fresh tables
    Base.metadata.create_all(bind=engine)
    yield
    # We can clean up if desired

def test_dashboard_stats_endpoint():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_invoices" in data
    assert "valid_invoices" in data
    assert "flagged_invoices" in data
    assert "high_value_invoices" in data

def test_demo_seed_endpoint():
    response = client.post("/api/invoices/demo/seed")
    assert response.status_code == 201
    data = response.json()
    assert "seeded_ids" in data
    assert len(data["seeded_ids"]) == 4

def test_list_invoices():
    # Seed first
    client.post("/api/invoices/demo/seed")
    response = client.get("/api/invoices")
    assert response.status_code == 200
    invoices = response.json()
    assert len(invoices) >= 4

def test_get_single_invoice_and_validation():
    # Seed
    seed_res = client.post("/api/invoices/demo/seed")
    first_id = seed_res.json()["seeded_ids"][0]

    # Get details
    res = client.get(f"/api/invoices/{first_id}")
    assert res.status_code == 200
    inv = res.json()
    assert inv["id"] == first_id
    assert inv["vendor_name"] is not None

    # Get validation checks
    val_res = client.get(f"/api/invoices/{first_id}/validation")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert "checks" in val_data

def test_review_and_revalidate_invoice():
    # Seed
    seed_res = client.post("/api/invoices/demo/seed")
    # second id is the calculation mismatch invoice
    mismatch_id = seed_res.json()["seeded_ids"][1]

    # Check initially FLAGGED
    initial_res = client.get(f"/api/invoices/{mismatch_id}")
    assert initial_res.json()["status"] == "FLAGGED"

    # Now edit to fix the total (Subtotal 50000 + Tax 9000 = 59000)
    update_payload = {
        "vendor_name": "TechFab Hardware Solutions Corrected",
        "subtotal": 50000.0,
        "tax": 9000.0,
        "total": 59000.0,
        "line_items": [
            {
                "description": "Workstation GPU Accelerators",
                "quantity": 2.0,
                "unit_price": 25000.0,
                "amount": 50000.0
            }
        ]
    }
    put_res = client.put(f"/api/invoices/{mismatch_id}", json=update_payload)
    assert put_res.status_code == 200
    updated_inv = put_res.json()
    # Should now automatically re-validate to VALID!
    assert updated_inv["status"] == "VALID"
    assert updated_inv["total"] == 59000.0

def test_approve_and_reject():
    seed_res = client.post("/api/invoices/demo/seed")
    inv_id = seed_res.json()["seeded_ids"][0]

    # Approve
    app_res = client.post(f"/api/invoices/{inv_id}/approve")
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"

    # Reject
    rej_res = client.post(f"/api/invoices/{inv_id}/reject")
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"

def test_upload_invoice_file():
    pdf_path = Path("sample_invoices/1_valid_invoice.pdf")
    if not pdf_path.exists():
        pytest.skip("sample pdf not generated")

    with open(pdf_path, "rb") as f:
        res = client.post(
            "/api/invoices/upload",
            files={"file": ("1_valid_invoice.pdf", f, "application/pdf")}
        )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["source_filename"] == "1_valid_invoice.pdf"

def test_upload_invalid_extension():
    fake_file = b"This is a fake script"
    res = client.post(
        "/api/invoices/upload",
        files={"file": ("malicious.exe", fake_file, "application/octet-stream")}
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]
