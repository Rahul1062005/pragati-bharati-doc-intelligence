from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.question import Question, ConfidenceLevel
from app.schemas.question import ReviewQueueItemResponse, QuestionResponse
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/review", tags=["Review Queue & Validation"])

class ReviewUpdatePayload(BaseModel):
    question_text: Optional[str] = None
    detected_answer: Optional[str] = None
    confidence_level: Optional[ConfidenceLevel] = ConfidenceLevel.CONFIDENT
    clear_reasons: bool = True

@router.get("/documents/{document_id}/queue", response_model=List[ReviewQueueItemResponse])
def get_review_queue(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve questions requiring human review:
    - Low confidence (<0.8)
    - Uncertain or unmatched answers
    - Cross-page continuation splits
    - Missing options or question numbers
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    questions = db.query(Question).filter(
        Question.document_id == document_id,
        (Question.confidence_level != ConfidenceLevel.CONFIDENT) | (Question.review_reasons != [])
    ).order_by(Question.confidence_score.asc()).all()

    return [
        ReviewQueueItemResponse(
            question_id=q.id,
            document_id=q.document_id,
            question_number=q.question_number,
            question_text=q.question_text,
            confidence_score=q.confidence_score,
            confidence_level=q.confidence_level,
            review_reasons=q.review_reasons or [],
            source_pages=q.source_pages or []
        )
        for q in questions
    ]

@router.put("/questions/{question_id}", response_model=QuestionResponse)
def update_reviewed_question(
    question_id: str,
    payload: ReviewUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update and approve a reviewed question"""
    question = db.query(Question).join(Document).filter(
        Question.id == question_id,
        Document.user_id == current_user.id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    if payload.question_text is not None:
        question.question_text = payload.question_text
    if payload.detected_answer is not None:
        question.detected_answer = payload.detected_answer
        question.answer_source = "HUMAN_REVIEWED"
    if payload.confidence_level is not None:
        question.confidence_level = payload.confidence_level
        if payload.confidence_level == ConfidenceLevel.CONFIDENT:
            question.confidence_score = 1.0
    if payload.clear_reasons:
        question.review_reasons = []

    db.commit()
    db.refresh(question)
    return question
