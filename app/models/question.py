import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Enum, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class ConfidenceLevel(str, enum.Enum):
    CONFIDENT = "CONFIDENT"
    PARTIAL = "PARTIAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"

class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TRUE_FALSE = "TRUE_FALSE"
    SHORT_ANSWER = "SHORT_ANSWER"
    ESSAY = "ESSAY"
    NUMERICAL = "NUMERICAL"
    UNKNOWN = "UNKNOWN"

class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    question_number = Column(Integer, nullable=True, index=True)
    raw_number_label = Column(String(50), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), default=QuestionType.MULTIPLE_CHOICE)
    
    # Cross-page support: source_pages array e.g. [1, 2]
    source_pages = Column(JSON, default=list)
    
    # Confidence & Validation
    confidence_score = Column(Float, default=1.0)
    confidence_level = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.CONFIDENT, index=True)
    review_reasons = Column(JSON, default=list)  # e.g. ["split_across_pages", "missing_options"]
    
    # Answer matching
    detected_answer = Column(String(100), nullable=True)
    answer_explanation = Column(Text, nullable=True)
    answer_source = Column(String(100), nullable=True)  # INLINE, SEPARATE_KEY, UNMATCHED
    
    has_images_or_tables = Column(Boolean, default=False)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("Document", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan", order_by="Option.option_key")

class Option(Base):
    __tablename__ = "options"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_key = Column(String(10), nullable=False)  # A, B, C, D, etc.
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=True)

    question = relationship("Question", back_populates="options")

class AnswerKeyEntry(Base):
    __tablename__ = "answer_key_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    question_number = Column(Integer, nullable=False, index=True)
    correct_answer = Column(String(100), nullable=False)
    explanation = Column(Text, nullable=True)
    source_page = Column(Integer, default=1)
    raw_text = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="answer_keys")

class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(20), default="INFO")  # INFO, WARNING, ERROR
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="logs")
