import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.main import app

def test_live_app():
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # 1. Test Seed
    print("Testing /api/invoices/demo/seed...")
    res = client.post("/api/invoices/demo/seed")
    assert res.status_code == 201, f"Seed failed: {res.text}"
    print(f"Seed Success: {res.json()}")

    # 2. Test Dashboard Stats
    print("Testing /api/dashboard/stats...")
    stats_res = client.get("/api/dashboard/stats")
    assert stats_res.status_code == 200
    print(f"Stats: {stats_res.json()}")

    # 3. Test Dashboard HTML
    print("Testing /dashboard HTML page...")
    dash_page = client.get("/dashboard")
    assert dash_page.status_code == 200
    assert "Invoice Processing Operations" in dash_page.text

    # 4. Test Upload HTML
    print("Testing /upload HTML page...")
    upload_page = client.get("/upload")
    assert upload_page.status_code == 200
    assert "Upload Invoice Document" in upload_page.text

    # 5. Test Invoice Detail HTML
    print("Testing /invoices/1 HTML page...")
    detail_page = client.get("/invoices/1")
    assert detail_page.status_code == 200
    assert "Invoice Details & Validation Audit" in detail_page.text

    # 6. Test Review HTML
    print("Testing /invoices/1/review HTML page...")
    rev_page = client.get("/invoices/1/review")
    assert rev_page.status_code == 200
    assert "Human-in-the-Loop Invoice Review" in rev_page.text

    print("\nALL LIVE APPLICATION ENDPOINTS AND TEMPLATES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_live_app()
