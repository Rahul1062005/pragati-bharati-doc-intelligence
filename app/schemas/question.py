from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.question import ConfidenceLevel, QuestionType

class OptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    option_key: str
    option_text: str
    is_correct: Optional[bool] = None

class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    question_number: Optional[int] = None
    raw_number_label: Optional[str] = None
    question_text: str
    question_type: QuestionType
    source_pages: List[int] = Field(default_factory=list)
    confidence_score: float
    confidence_level: ConfidenceLevel
    review_reasons: List[str] = Field(default_factory=list)
    detected_answer: Optional[str] = None
    answer_explanation: Optional[str] = None
    answer_source: Optional[str] = None
    has_images_or_tables: bool = False
    options: List[OptionResponse] = Field(default_factory=list)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class QuestionListResponse(BaseModel):
    document_id: str
    total_count: int
    page: int
    page_size: int
    questions: List[QuestionResponse]

class AnswerKeyEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    question_number: int
    correct_answer: str
    explanation: Optional[str] = None
    source_page: int
    raw_text: Optional[str] = None
    created_at: datetime

class StructuredQuestionExport(BaseModel):
    """Clean system-independent export format specified in Problem Statement Section 7"""
    question_number: Optional[int] = None
    question: str
    options: List[str] = Field(default_factory=list)
    answer: Optional[str] = None
    source_pages: List[int] = Field(default_factory=list)
    confidence: float
    confidence_level: str
    review_reasons: List[str] = Field(default_factory=list)

class ReviewQueueItemResponse(BaseModel):
    question_id: str
    document_id: str
    question_number: Optional[int] = None
    question_text: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    review_reasons: List[str]
    source_pages: List[int]
