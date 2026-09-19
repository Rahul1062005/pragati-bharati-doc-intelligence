import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

class StorageService:
    def __init__(self, upload_dir: str = settings.STORAGE_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, file: UploadFile) -> str:
        filename = file.filename or "unknown"
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        if ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{ext}'. Supported formats: {', '.join(settings.allowed_extensions_list)}"
            )
        
        return ext

    async def save_upload(self, file: UploadFile) -> tuple[str, str, int]:
        ext = self.validate_file(file)
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        target_path = self.upload_dir / unique_name
        
        size = 0
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        
        with open(target_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                size += len(chunk)
                if size > max_bytes:
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
                    )
                buffer.write(chunk)
                
        return str(target_path), unique_name, size

    def get_file_bytes(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

storage_service = StorageService()
