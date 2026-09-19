import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Float, DateTime, ForeignKey, Enum, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DocumentType(str, enum.Enum):
    PDF = "PDF"
    IMAGE = "IMAGE"

class DocumentRole(str, enum.Enum):
    QUESTION_PAPER = "QUESTION_PAPER"
    ANSWER_KEY = "ANSWER_KEY"
    COMBINED = "COMBINED"
    SUPPLEMENTARY = "SUPPLEMENTARY"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    document_type = Column(Enum(DocumentType), nullable=False)
    document_role = Column(Enum(DocumentRole), default=DocumentRole.QUESTION_PAPER)
    
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, index=True)
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    page_count = Column(Integer, default=0)
    ocr_method_used = Column(String(100), default="heuristic_parser")
    
    # Summary extraction stats
    total_questions = Column(Integer, default=0)
    confident_questions = Column(Integer, default=0)
    review_required_questions = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("User", back_populates="documents")
    questions = relationship("Question", back_populates="document", cascade="all, delete-orphan", order_by="Question.question_number")
    answer_keys = relationship("AnswerKeyEntry", back_populates="document", cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")
    
    outgoing_relations = relationship(
        "DocumentRelation",
        foreign_keys="DocumentRelation.source_document_id",
        back_populates="source_document",
        cascade="all, delete-orphan"
    )
    incoming_relations = relationship(
        "DocumentRelation",
        foreign_keys="DocumentRelation.target_document_id",
        back_populates="target_document",
        cascade="all, delete-orphan"
    )
