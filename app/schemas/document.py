from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.document import DocumentStatus, DocumentType, DocumentRole
from app.models.relation import RelationType

class DocumentCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: str
    original_filename: str
    status: DocumentStatus
    message: str
    task_id: str
    created_at: datetime

class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: str
    original_filename: str
    status: DocumentStatus
    progress_percent: int
    error_message: Optional[str] = None
    page_count: int
    total_questions: int
    confident_questions: int
    review_required_questions: int
    created_at: datetime
    updated_at: datetime

class DocumentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    document_type: DocumentType
    document_role: DocumentRole
    status: DocumentStatus
    progress_percent: int
    error_message: Optional[str] = None
    page_count: int
    ocr_method_used: str
    total_questions: int
    confident_questions: int
    review_required_questions: int
    created_at: datetime
    updated_at: datetime

class DocumentRelateRequest(BaseModel):
    target_document_id: str
    relationship_type: RelationType = RelationType.ANSWER_KEY_FOR

class DocumentRelateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    relation_id: str
    source_document_id: str
    target_document_id: str
    relationship_type: RelationType
    message: str
    created_at: datetime
