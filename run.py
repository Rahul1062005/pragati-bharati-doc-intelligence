"""
Main Entry Point to start the Document Intelligence & Question Extraction Service.
Usage:
    python run.py
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("=" * 70)
    print("Starting Pragati Bharati Document Intelligence Service...")
    print(f"Server URL:        http://127.0.0.1:{settings.PORT}")
    print(f"Swagger API Docs:  http://127.0.0.1:{settings.PORT}/docs")
    print(f"ReDoc Docs:        http://127.0.0.1:{settings.PORT}/redoc")
    print(f"Visual Reviewer:   http://127.0.0.1:{settings.PORT}/")
    print("=" * 70)
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
