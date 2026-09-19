import re
import json
import httpx
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from app.core.config import settings
from app.services.doc_parser import DocumentParseResult, ParsedPage

@dataclass
class ExtractedOption:
    key: str
    text: str

@dataclass
class ExtractedQuestionData:
    question_number: Optional[int]
    raw_label: Optional[str]
    question_text: str
    question_type: str
    options: List[ExtractedOption] = field(default_factory=list)
    source_pages: List[int] = field(default_factory=list)
    confidence_score: float = 1.0
    confidence_level: str = "CONFIDENT"
    review_reasons: List[str] = field(default_factory=list)
    detected_answer: Optional[str] = None
    answer_explanation: Optional[str] = None
    answer_source: Optional[str] = None
    has_images: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractedAnswerKeyItem:
    question_number: int
    correct_answer: str
    explanation: Optional[str] = None
    source_page: int = 1
    raw_text: str = ""

@dataclass
class ExtractionResult:
    questions: List[ExtractedQuestionData]
    answer_keys: List[ExtractedAnswerKeyItem]
    method_used: str

class AIExtractionService:
    # Regex patterns for question detection
    QUESTION_START_REGEX = re.compile(
        r"^(?:(?:Q(?:uestion)?\.?\s*(\d+))|(\d+)[\.\)\:\-]\s+)(.*)",
        re.IGNORECASE
    )
    
    # Regex for options (A, B, C, D)
    OPTION_REGEX = re.compile(
        r"^(?:[\(\[]?([A-Ea-e])[\)\]\.\:]\s+)(.*)",
        re.IGNORECASE
    )

    # Regex for answer key headers
    ANSWER_KEY_HEADER_REGEX = re.compile(
        r"(?:(?:answer\s*keys?)|(?:solutions?)|(?:correct\s*answers?)|(?:key\s*answers?))",
        re.IGNORECASE
    )

    # Regex for answer key entry (e.g. 1. A, 1 - B, Q1: C, 1: (D))
    ANSWER_ITEM_REGEX = re.compile(
        r"(?:(?:Q(?:uestion)?\.?\s*(\d+))|(\d+))\s*[\.\:\-\)]\s*[\(\[]?([A-Ea-e]|True|False|[\w\s]{1,20})[\)\]]?",
        re.IGNORECASE
    )

    async def extract_from_document(
        self,
        parse_result: DocumentParseResult,
        file_path: Optional[str] = None
    ) -> ExtractionResult:
        """
        Main extraction entry point.
        Uses AI provider if configured, otherwise falls back to deterministic heuristic state-machine.
        """
        # If Gemini or OpenAI is configured and available:
        if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            try:
                ai_result = await self._extract_with_gemini(parse_result, file_path)
                if ai_result and ai_result.questions:
                    return ai_result
            except Exception as e:
                # Log and fallback gracefully
                print(f"External AI extraction failed, falling back to local engine: {e}")

        # Default local heuristic state-machine
        return self._extract_heuristic(parse_result)

    def _extract_heuristic(self, parse_result: DocumentParseResult) -> ExtractionResult:
        all_questions: List[ExtractedQuestionData] = []
        all_answer_keys: List[ExtractedAnswerKeyItem] = []

        current_question: Optional[ExtractedQuestionData] = None
        current_option: Optional[ExtractedOption] = None
        is_in_answer_key_section = False
        answer_section_page = 1

        for page in parse_result.pages:
            page_num = page.page_number
            lines = [line.strip() for line in page.text.split("\n") if line.strip()]

            for line in lines:
                # 1. Check if entering Answer Key section
                if self.ANSWER_KEY_HEADER_REGEX.search(line):
                    is_in_answer_key_section = True
                    answer_section_page = page_num
                    continue

                if is_in_answer_key_section:
                    # Parse answer key entries
                    for match in self.ANSWER_ITEM_REGEX.finditer(line):
                        q_num_str = match.group(1) or match.group(2)
                        ans_val = match.group(3).strip()
                        if q_num_str and ans_val:
                            try:
                                q_num = int(q_num_str)
                                all_answer_keys.append(ExtractedAnswerKeyItem(
                                    question_number=q_num,
                                    correct_answer=ans_val.upper(),
                                    source_page=page_num,
                                    raw_text=line
                                ))
                            except ValueError:
                                pass
                    continue

                # 2. Check for Question Start
                q_match = self.QUESTION_START_REGEX.match(line)
                if q_match:
                    # Finalize previous question if any
                    if current_question:
                        self._finalize_question(current_question)
                        all_questions.append(current_question)
                        current_question = None
                        current_option = None

                    q_num_str = q_match.group(1) or q_match.group(2)
                    q_num = int(q_num_str) if q_num_str and q_num_str.isdigit() else None
                    q_text = q_match.group(3).strip()

                    current_question = ExtractedQuestionData(
                        question_number=q_num,
                        raw_label=f"Q{q_num}" if q_num else None,
                        question_text=q_text,
                        question_type="MULTIPLE_CHOICE",
                        source_pages=[page_num]
                    )
                    continue

                # 3. Check for Option Start (A, B, C, D)
                opt_match = self.OPTION_REGEX.match(line)
                if opt_match and current_question:
                    opt_key = opt_match.group(1).upper()
                    opt_text = opt_match.group(2).strip()
                    current_option = ExtractedOption(key=opt_key, text=opt_text)
                    current_question.options.append(current_option)
                    if page_num not in current_question.source_pages:
                        current_question.source_pages.append(page_num)
                    continue

                # 4. Continuation line (Cross-line or Cross-page split)
                if current_question:
                    # Update source_pages for cross-page continuation
                    if page_num not in current_question.source_pages:
                        current_question.source_pages.append(page_num)

                    if current_option:
                        # Append to current option text
                        current_option.text += f" {line}"
                    else:
                        # Append to question text
                        current_question.question_text += f" {line}"

        # Finalize last active question
        if current_question:
            self._finalize_question(current_question)
            all_questions.append(current_question)

        # Fallback if document is scanned or text is scarce
        if not all_questions and parse_result.is_mostly_scanned:
            all_questions.append(
                ExtractedQuestionData(
                    question_number=None,
                    raw_label=None,
                    question_text="Document appears to be scanned or contains low-resolution image data. OCR review required.",
                    question_type="UNKNOWN",
                    source_pages=[1],
                    confidence_score=0.25,
                    confidence_level="NEEDS_REVIEW",
                    review_reasons=["scanned_or_low_quality_document", "low_ocr_confidence"]
                )
            )

        return ExtractionResult(
            questions=all_questions,
            answer_keys=all_answer_keys,
            method_used="heuristic_parser"
        )

    def _finalize_question(self, q: ExtractedQuestionData):
        """Calculate confidence scores and validation flags for a question"""
        reasons = []
        score = 1.0

        # Check question length
        if len(q.question_text.strip()) < 10:
            score -= 0.3
            reasons.append("question_text_too_short")

        # Check options
        if not q.options:
            q.question_type = "SHORT_ANSWER"
        elif len(q.options) < 4:
            score -= 0.2
            reasons.append("fewer_than_standard_options")
            q.question_type = "MULTIPLE_CHOICE"
        else:
            q.question_type = "MULTIPLE_CHOICE"

        # Check cross-page continuity
        if len(q.source_pages) > 1:
            reasons.append("split_across_pages")
            score -= 0.1  # slight deduction for human verification

        # Check missing question number
        if q.question_number is None:
            score -= 0.3
            reasons.append("missing_question_number")

        q.confidence_score = max(0.1, round(score, 2))
        if q.confidence_score >= 0.8 and not reasons:
            q.confidence_level = "CONFIDENT"
        elif q.confidence_score >= 0.5:
            q.confidence_level = "PARTIAL"
        else:
            q.confidence_level = "NEEDS_REVIEW"

        q.review_reasons = reasons

    async def _extract_with_gemini(self, parse_result: DocumentParseResult, file_path: Optional[str]) -> Optional[ExtractionResult]:
        """External Gemini Vision extraction when API key is provided"""
        # Formulate payload for Gemini 1.5/2.0 Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        
        prompt = (
            "You are a document intelligence extraction service for examination question banks. "
            "Extract all questions, their options, source pages, and answer keys. "
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "questions": [{"question_number": 1, "question_text": "...", "options": [{"key": "A", "text": "..."}], "question_type": "MULTIPLE_CHOICE", "source_pages": [1], "confidence_score": 0.95}],\n'
            '  "answer_keys": [{"question_number": 1, "correct_answer": "B", "explanation": "..."}]\n'
            "}"
        )

        full_text = "\n\n".join([f"--- Page {p.page_number} ---\n{p.text}" for p in parse_result.pages])

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"text": f"Document text:\n{full_text}"}
                ]
            }]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean markdown fences
            clean_json = re.sub(r"^```json\s*", "", content.strip())
            clean_json = re.sub(r"\s*```$", "", clean_json)
            parsed = json.loads(clean_json)

            questions = []
            for item in parsed.get("questions", []):
                opts = [ExtractedOption(key=o["key"], text=o["text"]) for o in item.get("options", [])]
                questions.append(ExtractedQuestionData(
                    question_number=item.get("question_number"),
                    raw_label=f"Q{item.get('question_number')}",
                    question_text=item.get("question_text", ""),
                    question_type=item.get("question_type", "MULTIPLE_CHOICE"),
                    options=opts,
                    source_pages=item.get("source_pages", [1]),
                    confidence_score=float(item.get("confidence_score", 0.9)),
                    confidence_level="CONFIDENT" if item.get("confidence_score", 0.9) >= 0.8 else "NEEDS_REVIEW"
                ))

            answer_keys = [
                ExtractedAnswerKeyItem(
                    question_number=a["question_number"],
                    correct_answer=a["correct_answer"],
                    explanation=a.get("explanation")
                )
                for a in parsed.get("answer_keys", [])
            ]

            return ExtractionResult(
                questions=questions,
                answer_keys=answer_keys,
                method_used="gemini_vision_ai"
            )

ai_extractor_service = AIExtractionService()
