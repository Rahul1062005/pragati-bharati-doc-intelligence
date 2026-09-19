import traceback
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentStatus
from app.models.question import Question, Option, AnswerKeyEntry, ProcessingLog, ConfidenceLevel, QuestionType
from app.services.doc_parser import doc_parser_service
from app.services.ai_extractor import ai_extractor_service
from app.services.answer_matcher import answer_matcher_service

class QuestionService:
    async def process_document_pipeline(self, db: Session, document_id: str):
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        try:
            # 1. Update status to PROCESSING
            doc.status = DocumentStatus.PROCESSING
            doc.progress_percent = 10
            self._log(db, doc.id, "INIT", "Document processing initiated", "INFO")
            
            # Ensure idempotency: clear any previous questions/answers for this document
            db.query(Question).filter(Question.document_id == doc.id).delete()
            db.query(AnswerKeyEntry).filter(AnswerKeyEntry.document_id == doc.id).delete()
            db.commit()

            # 2. Parse pages & layout
            ext = doc.original_filename.split(".")[-1].lower()
            parse_result = doc_parser_service.parse_document(doc.file_path, ext)
            doc.page_count = parse_result.page_count
            doc.progress_percent = 35
            self._log(
                db, doc.id, "PARSING",
                f"Parsed {parse_result.page_count} pages (Scanned flag: {parse_result.is_mostly_scanned})",
                "INFO"
            )
            db.commit()

            # 3. Extract questions & answer keys
            doc.progress_percent = 60
            extraction = await ai_extractor_service.extract_from_document(parse_result, doc.file_path)
            doc.ocr_method_used = extraction.method_used
            self._log(
                db, doc.id, "EXTRACTION",
                f"Extracted {len(extraction.questions)} questions and {len(extraction.answer_keys)} answer keys using {extraction.method_used}",
                "INFO"
            )
            db.commit()

            # 4. Match inline answer keys
            answer_matcher_service.match_inline_answers(extraction.questions, extraction.answer_keys)
            doc.progress_percent = 80
            self._log(db, doc.id, "MATCHING", "Completed answer key association", "INFO")
            db.commit()

            # 5. Persist Answer Keys
            for ak in extraction.answer_keys:
                ak_entry = AnswerKeyEntry(
                    document_id=doc.id,
                    question_number=ak.question_number,
                    correct_answer=ak.correct_answer,
                    explanation=ak.explanation,
                    source_page=ak.source_page,
                    raw_text=ak.raw_text
                )
                db.add(ak_entry)

            # 6. Persist Questions & Options
            confident_count = 0
            review_count = 0

            for q_data in extraction.questions:
                if q_data.confidence_level == "CONFIDENT":
                    confident_count += 1
                else:
                    review_count += 1

                # Parse question type enum
                try:
                    q_type = QuestionType(q_data.question_type)
                except Exception:
                    q_type = QuestionType.MULTIPLE_CHOICE

                try:
                    conf_level = ConfidenceLevel(q_data.confidence_level)
                except Exception:
                    conf_level = ConfidenceLevel.CONFIDENT

                question = Question(
                    document_id=doc.id,
                    question_number=q_data.question_number,
                    raw_number_label=q_data.raw_label,
                    question_text=q_data.question_text,
                    question_type=q_type,
                    source_pages=q_data.source_pages,
                    confidence_score=q_data.confidence_score,
                    confidence_level=conf_level,
                    review_reasons=q_data.review_reasons,
                    detected_answer=q_data.detected_answer,
                    answer_explanation=q_data.answer_explanation,
                    answer_source=q_data.answer_source,
                    has_images_or_tables=q_data.has_images,
                    metadata_json=q_data.metadata
                )
                db.add(question)
                db.flush()  # Generate question.id

                # Add options
                for opt in q_data.options:
                    is_corr = None
                    if q_data.detected_answer and opt.key.strip().upper() == q_data.detected_answer.strip().upper():
                        is_corr = True
                    option_row = Option(
                        question_id=question.id,
                        option_key=opt.key,
                        option_text=opt.text,
                        is_correct=is_corr
                    )
                    db.add(option_row)

            # 7. Update document summary and mark COMPLETED
            doc.total_questions = len(extraction.questions)
            doc.confident_questions = confident_count
            doc.review_required_questions = review_count
            doc.status = DocumentStatus.COMPLETED
            doc.progress_percent = 100
            self._log(
                db, doc.id, "COMPLETE",
                f"Extraction finished successfully: {confident_count} confident, {review_count} need review",
                "INFO"
            )
            db.commit()

        except Exception as exc:
            db.rollback()
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(exc)
                self._log(db, doc.id, "ERROR", f"Processing failed: {str(exc)}\n{traceback.format_exc()}", "ERROR")
                db.commit()
            print(f"Error processing document {document_id}: {exc}")

    def _log(self, db: Session, doc_id: str, stage: str, message: str, level: str = "INFO"):
        log_entry = ProcessingLog(
            document_id=doc_id,
            stage=stage,
            message=message,
            level=level
        )
        db.add(log_entry)

question_service = QuestionService()
