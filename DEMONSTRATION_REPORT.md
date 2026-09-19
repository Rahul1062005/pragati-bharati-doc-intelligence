# Demonstration Evidence & Audit Report
## Pragati Bharati Document Intelligence & Question Extraction Service

This report documents the verification and test execution of all 10 required demonstration scenarios defined in **Section 12 of the Problem Statement**.

---

### Verification Summary Table

| # | Demonstration Scenario | Status | Key Evidence / Metric |
|---|---|:---:|---|
| 1 | **Uploading a PDF** | **PASSED** | Returned HTTP `202 Accepted` with `document_id: 30ffd689-2c2f-4fec-a63e-f59cebcafe31` |
| 2 | **Uploading an Image** | **PASSED** | Accepted PNG format `sample_scanned_exam.png`, queued asynchronously |
| 3 | **Processing a Scanned / Low-Quality Document** | **PASSED** | Density analysis detected low text, marked `status: COMPLETED` with 1 item in review queue |
| 4 | **Extracting Multiple Questions** | **PASSED** | Segmented 3 distinct questions with headers `Q1`, `Q2`, `Q3` |
| 5 | **Handling a Question Spanning Multiple Pages** | **PASSED** | Stitched Question 2 across Page 1 & Page 2, registered `source_pages: [1, 2]` |
| 6 | **Extracting Question Options** | **PASSED** | Extracted all 4 options (A, B, C, D) per question with clean option keys and text |
| 7 | **Detecting & Associating an Answer Key** | **PASSED** | Matched 3 inline answers; matched separate `sample_answer_key.pdf` via `/relate` API |
| 8 | **Showing Uncertain / Low-Confidence Extraction** | **PASSED** | Low-quality scan flagged with `confidence: 0.10`, `level: NEEDS_REVIEW`, reasons audit |
| 9 | **Retrieving Structured Question Data** | **PASSED** | Output conforms to Section 7 schema in `sample_outputs/sample_clean_output.json` |
| 10 | **Handling Invalid or Unsupported Document** | **PASSED** | Rejected `.txt` upload with HTTP `400 Bad Request` and clear validation error |

---

### Scenario Details & Terminal Evidence

#### Scenario 1: Uploading a PDF
```http
POST /api/v1/documents/upload HTTP/1.1
Content-Type: multipart/form-data
Authorization: Bearer <token>

[File: sample_clean_exam.pdf]

HTTP/1.1 202 Accepted
{
  "document_id": "30ffd689-2c2f-4fec-a63e-f59cebcafe31",
  "original_filename": "sample_clean_exam.pdf",
  "status": "PENDING",
  "message": "Document uploaded successfully. Background processing initiated.",
  "task_id": "task-30ffd689-2c2f-4fec-a63e-f59cebcafe31"
}
```

#### Scenario 2: Uploading an Image
```http
POST /api/v1/documents/upload HTTP/1.1
Content-Type: multipart/form-data
[File: sample_scanned_exam.png]

HTTP/1.1 202 Accepted
{
  "document_id": "7a51c459-91d8-42fa-9810-b857c4fe38c4",
  "status": "PENDING"
}
```

#### Scenario 3: Processing a Scanned / Low-Quality Document
- Density analyzer identifies scarce selectable text per page.
- Flags the document as `is_scanned: True`.
- Generates low confidence alert and routes question to the human review queue.

#### Scenario 4: Extracting Multiple Questions
- Three distinct questions extracted:
  - **Q1**: What is the time complexity of searching in a balanced Binary Search Tree? (4 options)
  - **Q2**: Which of the following HTTP status codes indicates 'Unauthorized'? (4 options)
  - **Q3**: In relational databases, ACID property 'I' stands for: (4 options)

#### Scenario 5: Handling a Question Spanning Multiple Pages
Input document: `sample_cross_page_split.pdf`
- Question 2 begins on Page 1: *"Consider a distributed message queue like Redis or Celery..."* with options A and B.
- Options C and D continue on Page 2 without a new question number prefix.
- The state-machine stitcher merges them and sets:
  ```json
  {
    "question_number": 2,
    "source_pages": [1, 2],
    "review_reasons": ["split_across_pages"]
  }
  ```

#### Scenario 6: Extracting Question Options
Options are normalized into structured items:
```json
[
  {"option_key": "A", "option_text": "O(1)", "is_correct": false},
  {"option_key": "B", "option_text": "O(log n)", "is_correct": true},
  {"option_key": "C", "option_text": "O(n)", "is_correct": false},
  {"option_key": "D", "option_text": "O(n log n)", "is_correct": false}
]
```

#### Scenario 7: Detecting & Associating an Answer Key
1. **Inline Detection**: Section header *"Answer Key & Solutions"* matched answers: 1-B, 2-C, 3-B.
2. **Standalone Document Association**: Paired `sample_answer_key.pdf` with the question paper through `POST /api/v1/documents/{id}/relate`.

#### Scenario 8: Showing Uncertain / Low-Confidence Extraction
Retrieved from `/api/v1/review/documents/{id}/queue`:
```json
{
  "question_id": "97e6bfad-...",
  "confidence_score": 0.1,
  "confidence_level": "NEEDS_REVIEW",
  "review_reasons": [
    "scanned_or_low_quality_document",
    "low_ocr_confidence",
    "unmatched_answer_key"
  ]
}
```

#### Scenario 9: Retrieving Final Structured Question Data (Section 7 Schema)
```json
[
  {
    "question_number": 1,
    "question": "What is the time complexity of searching in a balanced Binary Search Tree?",
    "options": [
      "A) O(1)",
      "B) O(log n)",
      "C) O(n)",
      "D) O(n log n)"
    ],
    "answer": "B",
    "source_pages": [1],
    "confidence": 1.0,
    "confidence_level": "CONFIDENT",
    "review_reasons": []
  }
]
```

#### Scenario 10: Handling Invalid or Unsupported Document
```http
POST /api/v1/documents/upload HTTP/1.1
[File: sample_invalid.txt]

HTTP/1.1 400 Bad Request
{
  "detail": "Unsupported file format '.txt'. Supported formats: pdf, png, jpg, jpeg"
}
```

---

### Conclusion

All 10 required demonstration scenarios have been executed, validated, and verified with zero defects.
