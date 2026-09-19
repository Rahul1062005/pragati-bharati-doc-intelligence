# Pragati Bharati - Document Intelligence & Question Extraction Service

A production-grade, scalable microservice built with **FastAPI**, **PostgreSQL**, **Redis**, and an intelligent **OCR / AI Document Pipeline** to ingest examination question papers (PDF & Images) and convert them into structured, machine-readable question banks.

---

## Key Highlights

- **FastAPI Core**: High-performance asynchronous REST API with automatic OpenAPI / Swagger UI documentation.
- **Asynchronous Processing**: Upload endpoints return `202 Accepted` immediately; documents are extracted asynchronously.
- **Cross-Page Question Continuity**: Detects and stitches questions that start on one page and continue onto the next.
- **Answer Key Association**: Automatically matches answers located at the end of a document, on separate pages, or in paired standalone answer key documents.
- **Dual Extraction Pipeline**:
  - **Offline Pure-Python Engine**: Powered by PyMuPDF (`pymupdf`) and layout heuristics — works 100% out of the box with zero external API dependencies.
  - **Multi-Modal AI Vision Engine**: Pluggable with Google Gemini Flash / OpenAI Vision for complex scans, diagrams, and handwriting via `.env`.
- **Confidence & Review System**: Scores extraction certainty (`0.0 - 1.0`), flagging uncertain or partial questions for human review.
- **Security & RBAC**: JWT Bearer authentication, isolated user authorization, multi-part file size and MIME validation.
- **Interactive Visual Reviewer**: Built-in modern web dashboard to upload, inspect real-time progress, view questions, and preview source pages.

---

## Quick Start Guide

### Option 1: Standalone Local Run (Recommended for Instant Evaluation)

1. **Clone or Navigate to the Project Directory**:
   ```bash
   cd "PBNC Project"
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate Sample Test Documents**:
   ```bash
   python generate_samples.py
   ```

4. **Run the Service**:
   ```bash
   python run.py
   ```
   The service will start at: **`http://localhost:8000`**

   - **Interactive Visual Dashboard**: `http://localhost:8000/`
   - **Swagger UI Interactive API**: `http://localhost:8000/docs`
   - **ReDoc API Documentation**: `http://localhost:8000/redoc`

---

### Option 2: Run with Docker Compose (PostgreSQL 16 + Redis 7 + FastAPI)

1. Ensure Docker Desktop is running.
2. Build and launch all services:
   ```bash
   docker compose up --build
   ```
3. The API and Visual Dashboard will be live at `http://localhost:8000`.

---

## How to Check and Validate the Backend

We provide 5 simple ways to verify that the backend is operating properly:

### 1. Automated Demonstration Script (All 10 Assignment Scenarios)
Run the automated end-to-end audit harness:
```bash
python run_demo.py
```
This script executes all 10 scenarios required by the assignment specification and outputs a color-coded verification report:
- Uploading a PDF
- Uploading an Image
- Processing a Scanned / Low-Quality Document
- Extracting Multiple Questions
- Handling Cross-Page Spanning Questions (`source_pages=[1, 2]`)
- Extracting Question Options
- Detecting and Associating Inline & Separate Answer Keys
- Flagging Low-Confidence Extractions
- Outputting Clean Structured JSON (Section 7 Schema)
- Demonstrating Error Handling for Invalid Files (400 Bad Request)

### 2. Automated Test Suite (Pytest)
Run the automated test suite with full verbose reporting:
```bash
pytest -v
```
All 16 tests covering authentication, upload validations, extraction, cross-page stitching, review queue, and relations will execute with green checkmarks.

### 3. Interactive Swagger UI (`/docs`)
Open `http://localhost:8000/docs`:
1. Use the **Authorize** button with the demo user:
   - **Username / Email**: `evaluator@pragatibharati.in`
   - **Password**: `EvaluatorPassword123!`
2. Test any endpoint interactively (e.g. upload documents, inspect status, retrieve questions, or export structured JSON).

### 4. Visual Dashboard UI (`/`)
Open `http://localhost:8000/`:
- Click **"⚡ One-Click Quick Demo User"** to log in instantly.
- Drag and drop any PDF/image from the `sample_data/` directory.
- Watch real-time asynchronous progress bars.
- Inspect extracted questions, correct option badges, confidence scores, and preview source pages.

### 5. Postman Collection
Import `postman_collection.json` into Postman. It includes pre-configured environment variables and test scripts for automated token capture.

---

## Directory Structure

```
PBNC Project/
├── app/
│   ├── api/
│   │   └── v1/             # API route controllers (auth, documents, questions, review)
│   ├── core/               # Configuration, security (JWT/bcrypt), database connections
│   ├── models/             # SQLAlchemy ORM models (User, Document, Question, Option, etc.)
│   ├── schemas/            # Pydantic validation and serialization schemas
│   ├── services/           # Business logic: storage, parser, AI extractor, answer matcher
│   ├── static/             # Visual Reviewer Dashboard (HTML, CSS, JS)
│   ├── workers/            # Task queue and async background workers
│   └── main.py             # FastAPI application initialization & middleware
├── sample_data/            # Sample test PDFs and images generated for the assignment
├── sample_outputs/         # Sample structured JSON outputs (Section 7 Schema)
├── tests/                  # Automated Pytest test suite (16 test cases)
├── ARCHITECTURE.md         # Detailed architectural documentation with Mermaid diagrams
├── DEMONSTRATION_REPORT.md # Evidence and output summary for the 10 demonstration scenarios
├── Dockerfile              # Production container build
├── docker-compose.yml      # Orchestration for FastAPI, PostgreSQL 16, and Redis 7
├── generate_samples.py     # Script to generate sample PDFs, splits, and scanned images
├── run_demo.py             # Automated runner verifying all 10 demonstration requirements
├── run.py                  # Server launcher
├── schema.sql              # Raw SQL DDL schema for PostgreSQL & SQLite
├── postman_collection.json # Postman collection
├── requirements.txt        # Python package dependencies
└── .env.example            # Environment configuration template
```

---

## API Surface Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/login/json` | Authenticate and obtain JWT Bearer token |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile |
| `POST` | `/api/v1/documents/upload` | Upload PDF or Image (returns `202 Accepted` with `document_id`) |
| `GET` | `/api/v1/documents` | List uploaded documents with status and metadata |
| `GET` | `/api/v1/documents/{id}/status` | Track asynchronous processing progress and metrics |
| `GET` | `/api/v1/documents/{id}/questions` | Retrieve extracted questions with filters (confidence, type) |
| `GET` | `/api/v1/questions/{question_id}` | Retrieve individual question detail |
| `GET` | `/api/v1/documents/{id}/answer-key` | Retrieve detected answer key entries |
| `GET` | `/api/v1/documents/{id}/export` | Export questions in clean Section 7 structured JSON format |
| `GET` | `/api/v1/review/documents/{id}/queue` | Retrieve questions flagged for human review |
| `PUT` | `/api/v1/review/questions/{id}` | Approve or update a reviewed question |
| `POST` | `/api/v1/documents/{id}/relate` | Associate related documents (e.g. Question Paper + Answer Key) |
| `GET` | `/health` | Healthcheck (Database and Queue status) |

---

## Structured Output Schema (Section 7 Specification)

Extracted questions are exported via `/api/v1/documents/{id}/export` adhering to the system-independent schema:

```json
[
  {
    "question_number": 1,
    "question": "What is the time complexity of searching in a balanced Binary Search Tree?",
    "options": [
      "A) O(1)",
      "B) O(log n)",
      "C) O(n)",
      "D) O(n log n)"
    ],
    "answer": "B",
    "source_pages": [1],
    "confidence": 1.0,
    "confidence_level": "CONFIDENT",
    "review_reasons": []
  }
]
```

---

## AI Vision Integration (Optional)

The application includes an offline parser that runs without external keys. To enable multi-modal AI Vision extraction:
1. Open `.env`
2. Set:
   ```env
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
3. Restart the server. Vision models will automatically handle complex handwriting, skewed scans, and mathematical diagrams.
