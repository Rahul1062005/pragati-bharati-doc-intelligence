from typing import List, Dict, Optional, Tuple
from app.services.ai_extractor import ExtractedQuestionData, ExtractedAnswerKeyItem
from app.models.question import Question, Option, AnswerKeyEntry
from sqlalchemy.orm import Session

class AnswerMatcherService:
    def match_inline_answers(
        self,
        questions: List[ExtractedQuestionData],
        answer_keys: List[ExtractedAnswerKeyItem]
    ):
        """Match answer keys detected within the same document to their questions"""
        key_map: Dict[int, ExtractedAnswerKeyItem] = {
            ak.question_number: ak for ak in answer_keys if ak.question_number is not None
        }

        for q in questions:
            if q.question_number in key_map:
                ak = key_map[q.question_number]
                q.detected_answer = ak.correct_answer
                q.answer_explanation = ak.explanation
                q.answer_source = f"INLINE_PAGE_{ak.source_page}"
                
                # Mark matching option if multiple choice
                for opt in q.options:
                    if opt.key.strip().upper() == ak.correct_answer.strip().upper():
                        # Marked as matched
                        pass
            else:
                q.answer_source = "UNMATCHED"
                q.review_reasons.append("unmatched_answer_key")
                q.confidence_score = max(0.1, round(q.confidence_score - 0.15, 2))
                if q.confidence_score < 0.8:
                    q.confidence_level = "NEEDS_REVIEW" if q.confidence_score < 0.5 else "PARTIAL"

    def match_from_related_document(
        self,
        db: Session,
        question_doc_id: str,
        answer_key_doc_id: str
    ) -> int:
        """
        Associate answer keys from a separate Answer Key document with questions in question_doc_id.
        """
        # Fetch answer keys from related document
        ak_entries = db.query(AnswerKeyEntry).filter(
            AnswerKeyEntry.document_id == answer_key_doc_id
        ).all()
        
        if not ak_entries:
            return 0

        key_map = {ak.question_number: ak for ak in ak_entries}
        
        # Fetch questions
        questions = db.query(Question).filter(
            Question.document_id == question_doc_id
        ).all()

        matched_count = 0
        for q in questions:
            if q.question_number in key_map:
                ak = key_map[q.question_number]
                q.detected_answer = ak.correct_answer
                q.answer_explanation = ak.explanation
                q.answer_source = f"EXTERNAL_DOC_{answer_key_doc_id}"
                
                # Update option is_correct
                for opt in q.options:
                    if opt.option_key.strip().upper() == ak.correct_answer.strip().upper():
                        opt.is_correct = True
                    else:
                        opt.is_correct = False

                # Remove unmatched flag if present
                if "unmatched_answer_key" in (q.review_reasons or []):
                    reasons = [r for r in q.review_reasons if r != "unmatched_answer_key"]
                    q.review_reasons = reasons
                    q.confidence_score = min(1.0, round(q.confidence_score + 0.15, 2))
                    if q.confidence_score >= 0.8:
                        q.confidence_level = "CONFIDENT"
                
                matched_count += 1

        db.commit()
        return matched_count

answer_matcher_service = AnswerMatcherService()
