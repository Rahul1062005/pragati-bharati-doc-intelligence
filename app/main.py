from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from app.core.config import settings
from app.core.database import init_db, engine
from app.api.v1.router import api_router
from app.workers.queue import task_queue

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    init_db()
    
    # Auto-seed demo evaluator account and sample documents on startup
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.document import Document, DocumentStatus, DocumentType, DocumentRole
    from app.services.question_service import question_service
    from generate_samples import generate_sample_documents

    # Ensure sample test documents exist on disk
    if not os.path.exists("sample_data/sample_clean_exam.pdf"):
        try:
            generate_sample_documents()
        except Exception as e:
            print("Sample generation warning:", e)

    db = SessionLocal()
    try:
        demo_email = "evaluator@pragatibharati.in"
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            user = User(
                email=demo_email,
                username="evaluator",
                hashed_password=hash_password("EvaluatorPassword123!")
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Pre-populate sample documents if user has none
        doc_count = db.query(Document).filter(Document.user_id == user.id).count()
        if doc_count == 0:
            for filename in ["sample_cross_page_split.pdf", "sample_clean_exam.pdf"]:
                fpath = f"sample_data/{filename}"
                if os.path.exists(fpath):
                    doc = Document(
                        user_id=user.id,
                        original_filename=filename,
                        stored_filename=filename,
                        file_path=fpath,
                        file_size_bytes=os.path.getsize(fpath),
                        mime_type="application/pdf",
                        document_type=DocumentType.PDF,
                        document_role=DocumentRole.QUESTION_PAPER,
                        status=DocumentStatus.PENDING,
                        progress_percent=0
                    )
                    db.add(doc)
                    db.commit()
                    db.refresh(doc)
                    await question_service.process_document_pipeline(db, doc.id)
    except Exception as exc:
        print("Startup seeding notice:", exc)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="""
    ## Pragati Bharati Document Intelligence & Question Extraction Service
    
    A production-oriented, scalable microservice to ingest examination papers and question banks
    in PDF (digital and scanned) and Image formats, converting them into structured, machine-readable
    question sets.
    
    ### Key Features:
    * **Asynchronous Document Ingestion**: Upload large documents without blocking clients.
    * **Automated Question Segmentation**: Detect question numbers, bodies, and options.
    * **Cross-Page Stitching**: Intelligently handles questions continuing across page breaks.
    * **Answer Key Matching**: Pairs answer keys from inline sections or standalone documents.
    * **Confidence & Review Pipeline**: Flags uncertain, partial, or low-quality extractions.
    * **Security & Auth**: JWT-based bearer authentication and user authorization isolation.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Static files for Visual Dashboard UI
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(str(static_path / "index.html"))

@app.get("/health", tags=["Health"])
def health_check():
    # Test DB connection
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        # For SQLAlchemy 2.0, text("SELECT 1") or simple ping
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e2:
            db_status = f"unhealthy: {str(e2)}"

    redis_status = "connected" if task_queue.redis_client else "local_async_worker"

    return {
        "status": "healthy" if "unhealthy" not in db_status else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": db_status,
        "queue_backend": redis_status,
        "allowed_extensions": settings.allowed_extensions_list
    }

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred.", "error": str(exc)},
    )
