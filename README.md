# AI Document and Invoice Processing Agent

An enterprise-grade, autonomous document and invoice processing agent built with **FastAPI**, **PyMuPDF**, **Tesseract OCR**, and **Multi-Modal AI LLMs** (Google Gemini & OpenAI). The system ingests invoices in PDF and image formats, extracts structured financial entities, validates accounting consistency and line-item math, identifies high-value risks, flags discrepancies, and empowers human auditors with a real-time review, correction, and approval dashboard.

---

## 🌟 Key Features

1. **Multi-Modal Document Ingestion**:
   - Accepts **PDF, JPG, JPEG, PNG** documents (up to 15MB).
   - Fast native text extraction via **PyMuPDF** (`fitz`).
   - Scanned PDF detection with automatic page image rendering and **Tesseract OCR fallback**.
2. **AI-Powered Structured Extraction**:
   - Strict JSON extraction conforming to typed Pydantic schemas.
   - Extracts: Vendor Name, Invoice Number, Invoice Date (normalized to `YYYY-MM-DD`), Currency, Line Items (description, quantity, unit price, amount), Subtotal, Tax, and Total.
   - Built-in multi-provider support: **Google Gemini**, **OpenAI**, and an intelligent **Demo/Fallback Extractor** that operates offline with zero API key dependencies.
3. **Rigorous Financial Validation Engine**:
   - **Required Fields Verification**: Checks for missing vendor, invoice number, date, or total.
   - **Line-Item Math Audit**: Verifies `quantity × unit_price = amount` (0.05 rounding tolerance).
   - **Subtotal Verification**: Compares sum of individual line items against stated subtotal.
   - **Tax & Total Consistency**: Audits `subtotal + tax = total`.
   - **Date Range & Format Validation**: Ensures calendar sanity.
   - **High-Value Risk Detection**: Flags any invoice $\ge$ ₹100,000 (configurable via environment variable) and triggers instant alerts.
4. **Autonomous Agent Decision Matrix**:
   - Assigns unambiguous statuses: `VALID`, `FLAGGED`, `REVIEW_REQUIRED`, `APPROVED`, `REJECTED`, or `PROCESSING_ERROR`.
5. **Modern Interactive Dashboard**:
   - Dark-mode responsive operations console.
   - Real-time KPI summary cards, discrepancy alert stream, and filterable invoice table.
   - Drag-and-drop upload zone with animated pipeline execution steps.
   - Human-in-the-loop review interface with inline table editing, dynamic recalculation, and instant re-validation.
6. **Built-in Demo Evaluation Kit**:
   - 1-click evaluation seeder populating:
     1. Fully balanced valid invoice.
     2. Calculation mismatch invoice (triggers `FLAGGED`).
     3. High-value enterprise invoice (triggers `HIGH_VALUE` alert).
     4. Missing required fields invoice.

---

## 🏗️ Architecture Diagram

```mermaid
flowchart TD
    User([User / Evaluator]) -->|Upload PDF / Image| Frontend[Web UI Dashboard]
    Frontend -->|POST /api/invoices/upload| FastAPI[FastAPI REST API]
    
    FastAPI --> Storage[Storage Service\n- Path Traversal Sanitization\n- File Size & Format Check]
    Storage --> Orchestrator[Agent Orchestrator\nagent_service.py]
    
    Orchestrator --> TypeDetect{Document Type}
    TypeDetect -->|Digital PDF| PyMuPDF[PyMuPDF Service\nNative Text Extraction]
    TypeDetect -->|Scanned PDF / Image| OCR[Tesseract OCR Engine\nPage Image Rendering]
    PyMuPDF -->|Scanned / Empty Text| OCR
    
    PyMuPDF --> RawText[Document Text Stream]
    OCR --> RawText
    
    RawText --> AIExtract{AI Service Layer}
    AIExtract -->|AI_API_KEY Configured| LLM[Gemini / OpenAI API\nStrict JSON Schema]
    AIExtract -->|Demo / Offline Mode| Fallback[Demo Fallback Extractor\nRegex & Heuristic Parser]
    
    LLM --> PydanticSchema[Pydantic Structured Schema\nInvoiceExtractionSchema]
    Fallback --> PydanticSchema
    
    PydanticSchema --> ValidationEngine[Validation Engine\nvalidation_service.py]
    
    subgraph ValidationEngineSub [Validation Rules & Calculations]
        V1[Required Fields Check]
        V2[Date Format & Range]
        V3[Line Item qty * price = amount]
        V4[Subtotal = sum line items]
        V5[Subtotal + Tax = Total]
        V6[Confidence Threshold]
    end
    
    ValidationEngine --> ValidationEngineSub
    ValidationEngineSub --> BranchDecision{Decision Branch}
    
    BranchDecision -->|Calculations Fail / Missing Fields| Flagged[Status: FLAGGED]
    BranchDecision -->|Low Confidence / Warnings| ReviewReq[Status: REVIEW_REQUIRED]
    BranchDecision -->|All Checks Pass| Valid[Status: VALID]
    BranchDecision -->|Extraction / Parsing Crash| Error[Status: PROCESSING_ERROR]
    
    Flagged --> HighValCheck{Total >= Threshold?}
    ReviewReq --> HighValCheck
    Valid --> HighValCheck
    
    HighValCheck -->|Yes >= ₹100k| HighValAlert[Mark high_value = True\nTrigger HIGH_VALUE Alert]
    HighValCheck -->|No| DBStore[Database Persistence\nSQLAlchemy SQLite/PostgreSQL]
    HighValAlert --> DBStore
    
    DBStore --> AlertRouter[Alert Service]
    AlertRouter -->|Console & In-Memory| DashboardAlerts[Dashboard Alert Stream]
    AlertRouter -->|SMTP Configured| EmailAlert[Email Notification]
    
    DBStore --> SheetsRouter[Google Sheets Module]
    SheetsRouter -->|Creds Configured| GoogleSheet[Append Invoice Row]
    SheetsRouter -->|Not Configured| SheetsSkip[Skip Gracefully]
    
    DBStore --> Response[API Response to UI]
    Response --> ReviewUI[Review / Edit Screen\nHuman-in-the-Loop]
    ReviewUI -->|Edit & Re-validate| PutAPI[PUT /api/invoices/:id]
    PutAPI --> ValidationEngine
    ReviewUI -->|User Approval| Approved[Status: APPROVED]
    ReviewUI -->|User Rejection| Rejected[Status: REJECTED]
```

---

## 💻 Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Jinja2
- **Document Processing**: PyMuPDF (`pymupdf`), Pillow (`PIL`), Tesseract OCR (`pytesseract`)
- **AI & LLM**: Google Gemini REST API (`gemini-1.5-flash`), OpenAI API (`gpt-4o-mini`), and deterministic fallback engine
- **ORM & Database**: SQLAlchemy 2.0 (SQLite for zero-config dev, PostgreSQL-ready)
- **Data Validation & Schemas**: Pydantic v2
- **Frontend**: Vanilla HTML5, CSS3 (Modern Glassmorphic Dark UI), JavaScript (ES6+), FontAwesome Icons
- **Testing**: Pytest, Pytest-Asyncio, HTTPX

---

## 📁 Project Structure

```
invoice-processing-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI initialization, routing & exception handlers
│   ├── config.py                 # Pydantic Settings & environment variable configuration
│   ├── database.py               # SQLAlchemy database session & initialization
│   ├── models.py                 # Invoice & InvoiceItem database models
│   ├── schemas.py                # Strict Pydantic validation & response schemas
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── invoice_routes.py     # Document upload, CRUD, approve, reject & demo seeding
│   │   ├── dashboard_routes.py   # Aggregated KPI stats & real-time alert queries
│   │   └── review_routes.py      # Jinja2 template views (Dashboard, Upload, Review, Detail)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py      # Master orchestrator agent coordinating all steps
│   │   ├── pdf_service.py        # PyMuPDF text parser and PDF page image renderer
│   │   ├── ocr_service.py        # Tesseract OCR processor with graceful fallback
│   │   ├── ai_extraction_service.py # LLM extraction layer (Gemini, OpenAI, Demo Fallback)
│   │   ├── validation_service.py # Deterministic math and accounting rule audit engine
│   │   ├── alert_service.py      # Structured discrepancy logging & email alerts
│   │   ├── storage_service.py    # Path traversal protection & file validation
│   │   ├── sheets_service.py     # Optional Google Sheets export integration
│   │   └── automation_service.py # Extensible email & folder watch daemon
│   │
│   ├── templates/
│   │   ├── base.html             # Common responsive sidebar & topbar layout
│   │   ├── dashboard.html        # KPI metrics, alert logs, and invoice table
│   │   ├── upload.html           # Drag-and-drop zone with animated pipeline tracker
│   │   ├── invoice_detail.html   # Detailed financial breakdown & audit checklist
│   │   └── review.html           # Human-in-the-loop review, inline edit & revalidation
│   │
│   └── static/
│       ├── css/
│       │   └── style.css         # Modern, high-performance CSS styling
│       └── js/
│           ├── dashboard.js      # Dashboard polling, filters, and demo seeder
│           ├── upload.js         # Uploader pipeline animations & sample document injectors
│           └── review.js         # Live calculations, re-validation, and approval triggers
│
├── sample_invoices/              # Pre-generated sample PDF & image test invoices
│   ├── 1_valid_invoice.pdf
│   ├── 2_mismatch_invoice.pdf
│   ├── 3_high_value_invoice.pdf
│   ├── 4_missing_vendor_invoice.pdf
│   └── 5_sample_receipt.png
│
├── scripts/
│   └── generate_samples.py       # Script to generate sample invoice PDF/images
│
├── tests/
│   ├── test_validation.py        # Math, line-item, tax, and date unit tests
│   ├── test_extraction.py        # Extraction schema and fallback tests
│   └── test_api.py               # Complete FastAPI endpoint integration tests
│
├── docs/
│   └── architecture.md           # In-depth architectural blueprint and Mermaid diagrams
│
├── uploads/                      # Secure storage directory for processed documents
├── .env.example                  # Environment configuration template
├── .env                          # Local runtime environment file
├── .gitignore                    # Git exclusions
├── requirements.txt              # Production dependency specifications
├── run.py                        # Standalone runner entry point
└── README.md                     # Project documentation
```

---

## ⚙️ Installation & Local Setup

### 1. Clone or Open the Repository
```bash
cd invoice-processing-agent
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration items in `.env`:
- `AI_API_KEY`: *(Optional)* Your Google Gemini or OpenAI API key. **If left blank, the system automatically runs in explicit DEMO/FALLBACK mode with realistic heuristic extraction.**
- `HIGH_VALUE_THRESHOLD`: Financial alert limit (default: `100000.0` INR).
- `DATABASE_URL`: `sqlite:///./invoices.db` (or PostgreSQL URL).

### 5. Generate Sample Invoices (Optional)
```bash
python scripts/generate_samples.py
```

### 6. Run the Application
```bash
python run.py
```
Or with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser and navigate to:
- **Web Dashboard**: `http://localhost:8000`
- **Upload Invoices**: `http://localhost:8000/upload`
- **Interactive Swagger API Docs**: `http://localhost:8000/docs`

---

## 🧪 Running Automated Tests

Run the full pytest suite:
```bash
pytest tests/ -v
```
All 17 tests validate upload validation, strict schema serialization, line-item calculation checks, subtotal and tax validation, date formatting, high-value alerts, and full REST API routes.

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/invoices/upload` | Upload and process PDF/image invoice through agent pipeline |
| `GET` | `/api/invoices` | List all processed invoices with optional `status_filter` |
| `GET` | `/api/invoices/{id}` | Retrieve full invoice details, line items, and audit trail |
| `PUT` | `/api/invoices/{id}` | Update invoice fields/items and automatically re-validate |
| `POST` | `/api/invoices/{id}/approve` | Mark invoice status as `APPROVED` |
| `POST` | `/api/invoices/{id}/reject` | Mark invoice status as `REJECTED` |
| `GET` | `/api/invoices/{id}/validation` | Retrieve granular rule check results |
| `DELETE` | `/api/invoices/{id}` | Delete invoice and associated line items |
| `POST` | `/api/invoices/demo/seed` | Seed the 4 evaluation test cases |
| `GET` | `/api/dashboard/stats` | Aggregated KPI counts and totals |
| `GET` | `/api/dashboard/alerts` | Retrieve live system alert log |

---

## 🎬 Evaluation Demo Video Flow (Step-by-Step)

When demonstrating this project for an evaluation:

1. **Dashboard Overview (0:00 - 0:45)**:
   - Open `http://localhost:8000`. Show the statistics grid (Total, Valid, Flagged, Review Required, High Value).
   - Click **"Load 4 Sample Evaluation Cases"** to immediately populate the table and show how the dashboard dynamically updates.
2. **Reviewing Discrepancies & Flagged Invoices (0:45 - 1:45)**:
   - Click on the invoice with status **`FLAGGED`** (`INV-2026-002`).
   - Show the **Validation Engine Results** card on the right: points out exact calculation mismatch ($50,000 + 9,000 \ne 75,000$).
   - Click **"Review / Edit Invoice"**.
   - Correct the total to `59000.00` or click **"Auto-Balance Totals"**.
   - Click **"Save Changes & Re-validate"** $\rightarrow$ Show the status automatically update from `FLAGGED` to `VALID` with all green checkmarks!
   - Click **"Approve"** $\rightarrow$ Status changes to `APPROVED`.
3. **High-Value Detection & Alerts (1:45 - 2:30)**:
   - Go back to Dashboard. Highlight the **High-Value badge** and the **Agent Discrepancy & High-Value Alerts** stream showing the ₹295,000 invoice alert.
4. **Live Document Ingestion Pipeline (2:30 - 3:30)**:
   - Navigate to `/upload`.
   - Click on one of the sample invoice test helpers (or drag a file from `sample_invoices/`).
   - Click **"Process Invoice"**.
   - Watch the animated step-by-step agent tracker:
     - Step 1: Upload & File Validation
     - Step 2: Native Text / OCR
     - Step 3: AI Structured Extraction
     - Step 4: Calculations & Accounting Rules
     - Step 5: Storage & Alerts
   - Click **"View Invoice"** to inspect the parsed line items and audit checklist.
5. **API & Code Walkthrough (3:30 - 4:00)**:
   - Briefly show `http://localhost:8000/docs` to demonstrate clean OpenAPI/Swagger specification.

---

## 🚀 Cloud Deployment (e.g., Render / Railway / Docker)

### Render Deployment Instructions:
1. Push repository to GitHub.
2. On [Render](https://render.com), create a new **Web Service** linked to your repository.
3. Configure the service:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In **Environment Variables**:
   - `HIGH_VALUE_THRESHOLD`: `100000.0`
   - `AI_API_KEY`: *(Optional)* your Gemini/OpenAI key.
   - `DATABASE_URL`: Provide a PostgreSQL connection string for production persistence (e.g. `postgresql://user:password@host:5432/dbname`).

---

## 🔮 Future Enhancements

- **Autonomous Email Ingestion**: Background IMAP/Gmail API worker to ingest attached invoices automatically from `inbox@company.com`.
- **ERP Integration**: Direct webhook sync into QuickBooks, SAP, and Xero.
- **Two-Way Cross-Matching**: Automated matching against Purchase Orders (PO) and Goods Receipt Notes (GRN).
