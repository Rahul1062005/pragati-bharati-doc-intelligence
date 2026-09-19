import pytest
import time
import asyncio
from pathlib import Path
from fastapi import status
from app.services.question_service import question_service

def test_clean_pdf_extraction_pipeline(client, auth_headers, db_session):
    # Upload clean exam PDF
    clean_pdf = Path("sample_data/sample_clean_exam.pdf")
    with open(clean_pdf, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("sample_clean_exam.pdf", f, "application/pdf")}
        )
    assert res.status_code == status.HTTP_202_ACCEPTED
    doc_id = res.json()["document_id"]

    # Run processing pipeline directly in test
    asyncio.run(question_service.process_document_pipeline(db_session, doc_id))

    # Check status
    status_res = client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert status_res.status_code == status.HTTP_200_OK
    status_data = status_res.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["total_questions"] == 3
    assert status_data["confident_questions"] >= 2

    # Check extracted questions
    q_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers=auth_headers)
    assert q_res.status_code == status.HTTP_200_OK
    questions = q_res.json()["questions"]
    assert len(questions) == 3
    for q in questions:
        assert len(q["options"]) == 4
        assert q["detected_answer"] in ["B", "C"]
        assert q["confidence_level"] == "CONFIDENT"

def test_cross_page_split_extraction(client, auth_headers, db_session):
    split_pdf = Path("sample_data/sample_cross_page_split.pdf")
    with open(split_pdf, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("sample_cross_page_split.pdf", f, "application/pdf")}
        )
    assert res.status_code == status.HTTP_202_ACCEPTED
    doc_id = res.json()["document_id"]

    # Process pipeline
    asyncio.run(question_service.process_document_pipeline(db_session, doc_id))

    # Fetch questions
    q_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers=auth_headers)
    assert q_res.status_code == status.HTTP_200_OK
    questions = q_res.json()["questions"]
    assert len(questions) == 3

    # Question 2 is split across Page 1 and Page 2
    q2 = next(q for q in questions if q["question_number"] == 2)
    assert len(q2["options"]) == 4
    assert 1 in q2["source_pages"] and 2 in q2["source_pages"]
    assert "split_across_pages" in q2["review_reasons"]

def test_separate_answer_key_association(client, auth_headers, db_session):
    # 1. Upload Question Paper
    clean_pdf = Path("sample_data/sample_clean_exam.pdf")
    with open(clean_pdf, "rb") as f:
        res1 = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("question_paper.pdf", f, "application/pdf")}
        )
    qp_id = res1.json()["document_id"]
    asyncio.run(question_service.process_document_pipeline(db_session, qp_id))

    # 2. Upload Standalone Answer Key
    ak_pdf = Path("sample_data/sample_answer_key.pdf")
    with open(ak_pdf, "rb") as f:
        res2 = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={"document_role": "ANSWER_KEY"},
            files={"file": ("sample_answer_key.pdf", f, "application/pdf")}
        )
    ak_id = res2.json()["document_id"]
    asyncio.run(question_service.process_document_pipeline(db_session, ak_id))

    # 3. Associate via /relate endpoint
    rel_res = client.post(
        f"/api/v1/documents/{ak_id}/relate",
        headers=auth_headers,
        json={"target_document_id": qp_id, "relationship_type": "ANSWER_KEY_FOR"}
    )
    assert rel_res.status_code == status.HTTP_200_OK
    assert "associated successfully" in rel_res.json()["message"]
