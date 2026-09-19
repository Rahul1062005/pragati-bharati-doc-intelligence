import pytest
import time
from fastapi import status
from pathlib import Path

def test_upload_invalid_extension(client, auth_headers):
    invalid_file = Path("sample_data/sample_invalid.txt")
    with open(invalid_file, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("sample_invalid.txt", f, "text/plain")}
        )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported file format" in res.json()["detail"]

def test_upload_without_auth(client):
    clean_pdf = Path("sample_data/sample_clean_exam.pdf")
    with open(clean_pdf, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample_clean_exam.pdf", f, "application/pdf")}
        )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

def test_upload_pdf_success(client, auth_headers):
    clean_pdf = Path("sample_data/sample_clean_exam.pdf")
    with open(clean_pdf, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("sample_clean_exam.pdf", f, "application/pdf")}
        )
    assert res.status_code == status.HTTP_202_ACCEPTED
    data = res.json()
    assert "document_id" in data
    assert data["status"] in ["PENDING", "PROCESSING", "COMPLETED"]
    assert "task_id" in data

def test_upload_image_success(client, auth_headers):
    img_file = Path("sample_data/sample_scanned_exam.png")
    with open(img_file, "rb") as f:
        res = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("sample_scanned_exam.png", f, "image/png")}
        )
    assert res.status_code == status.HTTP_202_ACCEPTED
    assert "document_id" in res.json()

def test_list_documents(client, auth_headers):
    res = client.get("/api/v1/documents", headers=auth_headers)
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 2
