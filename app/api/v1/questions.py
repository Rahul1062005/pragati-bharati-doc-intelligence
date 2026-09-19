from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.question import Question, Option, AnswerKeyEntry, ConfidenceLevel, QuestionType
from app.schemas.question import (
    QuestionResponse,
    QuestionListResponse,
    AnswerKeyEntryResponse,
    StructuredQuestionExport
)
from app.api.v1.deps import get_current_user

router = APIRouter(tags=["Questions & Answers"])

@router.get("/documents/{document_id}/questions", response_model=QuestionListResponse)
def get_document_questions(
    document_id: str,
    confidence_filter: Optional[ConfidenceLevel] = None,
    question_type: Optional[QuestionType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all extracted questions for a document with optional filters and pagination"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    query = db.query(Question).filter(Question.document_id == document_id)
    if confidence_filter:
        query = query.filter(Question.confidence_level == confidence_filter)
    if question_type:
        query = query.filter(Question.question_type == question_type)

    total_count = query.count()
    offset = (page - 1) * page_size
    questions = query.order_by(Question.question_number.asc()).offset(offset).limit(page_size).all()

    return QuestionListResponse(
        document_id=document_id,
        total_count=total_count,
        page=page,
        page_size=page_size,
        questions=questions
    )

@router.get("/questions/{question_id}", response_model=QuestionResponse)
def get_single_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve full details of a specific question"""
    question = db.query(Question).join(Document).filter(
        Question.id == question_id,
        Document.user_id == current_user.id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
    return question

@router.get("/documents/{document_id}/answer-key", response_model=List[AnswerKeyEntryResponse])
def get_document_answer_key(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve extracted answer key entries for a document"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return db.query(AnswerKeyEntry).filter(
        AnswerKeyEntry.document_id == document_id
    ).order_by(AnswerKeyEntry.question_number.asc()).all()

@router.get("/documents/{document_id}/export", response_model=List[StructuredQuestionExport])
def export_questions_structured(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns questions in the clean, system-independent schema specified in
    Problem Statement Section 7.
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    questions = db.query(Question).filter(
        Question.document_id == document_id
    ).order_by(Question.question_number.asc()).all()

    output = []
    for q in questions:
        formatted_options = [f"{opt.option_key}) {opt.option_text}" for opt in q.options]
        output.append(StructuredQuestionExport(
            question_number=q.question_number,
            question=q.question_text,
            options=formatted_options,
            answer=q.detected_answer,
            source_pages=q.source_pages or [],
            confidence=q.confidence_score,
            confidence_level=q.confidence_level.value,
            review_reasons=q.review_reasons or []
        ))
    return output
