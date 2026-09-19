from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentType, DocumentRole
from app.models.relation import DocumentRelation, RelationType
from app.schemas.document import (
    DocumentCreateResponse,
    DocumentStatusResponse,
    DocumentDetailResponse,
    DocumentRelateRequest,
    DocumentRelateResponse
)
from app.services.storage import storage_service
from app.services.doc_parser import doc_parser_service
from app.services.answer_matcher import answer_matcher_service
from app.workers.queue import task_queue
from app.workers.tasks import process_document_task
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    document_role: DocumentRole = Form(DocumentRole.QUESTION_PAPER),
    target_document_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF or Image asynchronously.
    Returns 202 Accepted immediately with document_id and tracking status.
    """
    ext = storage_service.validate_file(file)
    file_path, stored_filename, file_size = await storage_service.save_upload(file)

    doc_type = DocumentType.PDF if ext == "pdf" else DocumentType.IMAGE

    # Create document entry
    doc = Document(
        user_id=current_user.id,
        original_filename=file.filename or "unknown",
        stored_filename=stored_filename,
        file_path=file_path,
        file_size_bytes=file_size,
        mime_type=file.content_type or f"application/{ext}",
        document_type=doc_type,
        document_role=document_role,
        status=DocumentStatus.PENDING,
        progress_percent=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # If user provided a target document to relate to (e.g. associating this Answer Key to a Question Paper)
    if target_document_id:
        target_doc = db.query(Document).filter(
            Document.id == target_document_id,
            Document.user_id == current_user.id
        ).first()
        if target_doc:
            relation = DocumentRelation(
                source_document_id=doc.id,
                target_document_id=target_doc.id,
                relationship_type=RelationType.ANSWER_KEY_FOR
            )
            db.add(relation)
            db.commit()

    # Dispatch asynchronous background task
    task_queue.enqueue_task(process_document_task, doc.id)

    return DocumentCreateResponse(
        document_id=doc.id,
        original_filename=doc.original_filename,
        status=doc.status,
        message="Document uploaded successfully. Background processing initiated.",
        task_id=f"task-{doc.id}",
        created_at=doc.created_at
    )

@router.get("", response_model=List[DocumentDetailResponse])
def list_documents(
    status_filter: Optional[DocumentStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Document).filter(Document.user_id == current_user.id)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    return query.order_by(Document.created_at.desc()).all()

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_details(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc

@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def check_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentStatusResponse(
        document_id=doc.id,
        original_filename=doc.original_filename,
        status=doc.status,
        progress_percent=doc.progress_percent,
        error_message=doc.error_message,
        page_count=doc.page_count,
        total_questions=doc.total_questions,
        confident_questions=doc.confident_questions,
        review_required_questions=doc.review_required_questions,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )

@router.get("/{document_id}/page-preview/{page_num}")
def preview_page(
    document_id: str,
    page_num: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Render a page as PNG image for inspection or reviewer dashboard"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    ext = doc.original_filename.split(".")[-1].lower()
    if ext == "pdf":
        try:
            png_bytes = doc_parser_service.render_pdf_page_image(doc.file_path, page_num=page_num)
            return Response(content=png_bytes, media_type="image/png")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # For single image file, return original bytes
        image_bytes = storage_service.get_file_bytes(doc.file_path)
        return Response(content=image_bytes, media_type=doc.mime_type)

@router.post("/{document_id}/relate", response_model=DocumentRelateResponse)
def relate_documents(
    document_id: str,
    payload: DocumentRelateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Associate Answer Key document with Question Paper document and trigger cross-matching.
    """
    source_doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    target_doc = db.query(Document).filter(
        Document.id == payload.target_document_id,
        Document.user_id == current_user.id
    ).first()

    if not source_doc or not target_doc:
        raise HTTPException(status_code=404, detail="One or both documents not found.")

    relation = DocumentRelation(
        source_document_id=source_doc.id,
        target_document_id=target_doc.id,
        relationship_type=payload.relationship_type
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)

    # If source is answer key and target is question paper, apply matching
    matched_count = answer_matcher_service.match_from_related_document(
        db,
        question_doc_id=target_doc.id,
        answer_key_doc_id=source_doc.id
    )

    return DocumentRelateResponse(
        relation_id=relation.id,
        source_document_id=source_doc.id,
        target_document_id=target_doc.id,
        relationship_type=relation.relationship_type,
        message=f"Documents associated successfully. {matched_count} questions matched with answer key.",
        created_at=relation.created_at
    )

@router.post("/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    task_queue.enqueue_task(process_document_task, doc.id)
    return {"message": "Document re-processing queued.", "document_id": doc.id}
