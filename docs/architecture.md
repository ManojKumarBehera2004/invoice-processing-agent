# AI Document and Invoice Processing Agent - Architecture

## System Architecture Overview

The system is built as an autonomous, modular AI document processing agent capable of handling diverse financial document formats (PDFs, scanned images, multi-page bills), performing intelligent OCR and multi-modal AI extraction, validating strict business and accounting rules, detecting calculation discrepancies, raising real-time alerts, and enabling a seamless human-in-the-loop review workflow.

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

## Processing Decision Logic & Status Matrix

| Check Condition | Severity | System Action | Result Status |
| :--- | :--- | :--- | :--- |
| **Missing Vendor, Inv #, Date, or Total** | Critical Error | Check `required_fields` marked FAIL | `FLAGGED` |
| **Line Item Calculation Mismatch** (`qty × price ≠ amount`) | Calculation Error | Check `line_items` marked FAIL | `FLAGGED` |
| **Subtotal Sum Mismatch** (`sum(items) ≠ subtotal`) | Calculation Error | Check `subtotal` marked FAIL | `FLAGGED` |
| **Total Mismatch** (`subtotal + tax ≠ total`) | Calculation Error | Check `total` & `tax` marked FAIL | `FLAGGED` |
| **Total Amount ≥ Threshold** (e.g. ₹100,000) | Financial Risk | `high_value = True`, Dispatch Alert | Retains base status + High Value badge |
| **Extraction Confidence < 0.75** | Advisory | Added to warnings list | `REVIEW_REQUIRED` |
| **All Checks Balanced & Pass** | Normal | Verified | `VALID` |
| **Human Auditor Verifies & Approves** | Manual Action | Audit log updated | `APPROVED` |
| **Human Auditor Rejects** | Manual Action | Audit log updated | `REJECTED` |

---

## Component Separation

1. **`app/services/pdf_service.py`**:
   - PyMuPDF native page extraction.
   - Heuristic scanned PDF detection (`len(text) < 40 chars`).
   - High-DPI page rendering to PIL images for OCR.

2. **`app/services/ocr_service.py`**:
   - Tesseract OCR interface with PSM modes.
   - Graceful host fallback if binary is absent on machine.

3. **`app/services/ai_extraction_service.py`**:
   - Provider abstraction: Gemini, OpenAI, Demo Fallback.
   - Schema enforcement via Pydantic.
   - Explicit `extraction_mode` logging.

4. **`app/services/validation_service.py`**:
   - Deterministic mathematical and business rule verification.
   - Decimal rounding tolerance (0.05).

5. **`app/services/alert_service.py`**:
   - Alert stream logging and optional SMTP dispatch.

6. **`app/services/sheets_service.py`**:
   - Optional Google Sheets export with graceful non-configured status.
