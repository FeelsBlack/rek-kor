# Finance RPA Architecture

## System Architecture Diagram

```mermaid
graph TD;
    User[User / Client] -->|Uploads PDF/Image| UI[Streamlit UI];
    UI -->|POST /process-document| API[FastAPI Backend];

    API -->|1. Convert to Image| Processor[Extraction Service];
    Processor -->|2. Send Images + Prompt| Gemini[Google Gemini 1.5 Flash Vision API];
    Gemini -->|3. Return Structured JSON| Processor;
    Processor -->|4. Save to DB| DB[(PostgreSQL Database)];

    API -->|Validation| Validator[Validation Service];
    Validator -->|Check balances & alignments| DB;

    UI -->|POST /reconcile with ERP data| API;
    API -->|Fetch Statement| DB;
    API -->|Reconcile| ReconService[Reconciliation Service (Pandas)];
    ReconService -->|Return matched/unmatched| UI;
    ReconService -->|Save Report| DB;
```

## Folder Structure

```
.
├── app/
│   ├── api/
│   │   └── endpoints.py         # FastAPI routes
│   ├── core/
│   │   └── config.py            # (Optional) Configuration settings
│   ├── db/
│   │   └── database.py          # SQLAlchemy setup
│   ├── models/
│   │   ├── db_models.py         # SQLAlchemy ORM models
│   │   └── schemas.py           # Pydantic schemas for JSON structure
│   ├── services/
│   │   ├── extraction_service.py # Gemini Vision integration & PDF handling
│   │   ├── reconciliation_service.py # ERP matching logic
│   │   └── validation_service.py # Balance & anomaly checks
│   ├── ui/
│   │   └── main.py              # Streamlit frontend application
│   └── main.py                  # FastAPI application entry point
├── docs/
│   └── architecture.md          # This file
├── docker-compose.yml           # Multi-container orchestration (DB, API, UI)
├── Dockerfile                   # Docker build instructions for Python services
└── requirements.txt             # Python dependencies
```

## Sample API Endpoints

### 1. `POST /api/v1/process-document`
- **Description:** Uploads a PDF or image, processes it via Gemini, and saves to the database.
- **Request:** `multipart/form-data` with key `file`.
- **Response:** The `StatementSchema` JSON.

### 2. `POST /api/v1/validate`
- **Description:** Validates extracted statement data for consistency.
- **Request JSON:** `StatementSchema`
- **Response JSON:** `ValidationResult` (contains boolean `is_valid` and list of `anomalies`).

### 3. `POST /api/v1/reconcile`
- **Description:** Reconciles a bank statement stored in the DB against external ERP Accounts Payable data.
- **Request JSON:**
```json
{
  "statement_id": 1,
  "erp_data": [
    {"date": "2023-01-05", "description": "Vendor A", "amount": 150.0}
  ]
}
```
- **Response JSON:** `ReconciliationResult` (contains `matched`, `unmatched_statement`, `unmatched_erp`, `suspected_duplicates`).


## Core Extraction Prompt (Gemini Vision)

This prompt forces the multi-modal LLM to act as an OCR engine and layout parser, returning *only* valid JSON.

```text
You are a highly capable financial data extraction assistant.
Your task is to extract information from the provided bank statement image(s) and return it EXACTLY in the requested JSON structure.

Analyze the layout, tables, and text to accurately extract the following fields. Do not invent data; if a field is missing, leave it as an empty string (or 0 for numbers).

Ensure the output is a raw JSON object matching this schema:
{
  "bank_name": "string",
  "account_number": "string",
  "account_holder": "string",
  "statement_period": "string",
  "transactions": [
    {
      "date": "string (e.g., YYYY-MM-DD or as written)",
      "description": "string",
      "debit": float (0 if none),
      "credit": float (0 if none),
      "balance": float (0 if missing)
    }
  ]
}

IMPORTANT: Return ONLY the JSON object. Do not include markdown formatting like ```json or any other text.
```
