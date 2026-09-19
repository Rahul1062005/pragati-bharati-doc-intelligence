import pytest
import asyncio
from pathlib import Path
from fastapi import status
from app.services.question_service import question_service

def test_scanned_image_review_flagging(client, auth_headers, db_session):
    img_file = Path("sample_data/sample_scanned_exam.png")
    with open(img_file, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("sample_scanned_exam.png", f, "image/png")}
        )
    assert res.status_code == status.HTTP_202_ACCEPTED
    doc_id = res.json()["document_id"]
    asyncio.run(question_service.process_document_pipeline(db_session, doc_id))

    # Retrieve review queue
    review_res = client.get(f"/api/v1/review/documents/{doc_id}/queue", headers=auth_headers)
    assert review_res.status_code == status.HTTP_200_OK
    queue_items = review_res.json()
    assert len(queue_items) >= 1
    assert queue_items[0]["confidence_level"] == "NEEDS_REVIEW"
    assert "scanned_or_low_quality_document" in queue_items[0]["review_reasons"]

def test_update_and_approve_reviewed_question(client, auth_headers, db_session):
    # Get a question from previously uploaded split exam
    clean_pdf = Path("sample_data/sample_clean_exam.pdf")
    with open(clean_pdf, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("exam.pdf", f, "application/pdf")}
        )
    doc_id = res.json()["document_id"]
    asyncio.run(question_service.process_document_pipeline(db_session, doc_id))

    # Get questions
    q_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers=auth_headers)
    q_id = q_res.json()["questions"][0]["id"]

    # Update through review endpoint
    up_res = client.put(
        f"/api/v1/review/questions/{q_id}",
        headers=auth_headers,
        json={
            "question_text": "Updated question text by human reviewer",
            "detected_answer": "B",
            "confidence_level": "CONFIDENT",
            "clear_reasons": True
        }
    )
    assert up_res.status_code == status.HTTP_200_OK
    data = up_res.json()
    assert data["question_text"] == "Updated question text by human reviewer"
    assert data["confidence_score"] == 1.0

def test_structured_export_endpoint(client, auth_headers, db_session):
    clean_pdf = Path("sample_data/sample_clean_exam.pdf")
    with open(clean_pdf, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("export_test.pdf", f, "application/pdf")}
        )
    doc_id = res.json()["document_id"]
    asyncio.run(question_service.process_document_pipeline(db_session, doc_id))

    # Request export format
    exp_res = client.get(f"/api/v1/documents/{doc_id}/export", headers=auth_headers)
    assert exp_res.status_code == status.HTTP_200_OK
    exported = exp_res.json()
    assert len(exported) == 3
    # Check Section 7 fields: question, options, answer, source_pages, confidence
    for item in exported:
        assert "question" in item
        assert "options" in item
        assert "answer" in item
        assert "source_pages" in item
        assert "confidence" in item
