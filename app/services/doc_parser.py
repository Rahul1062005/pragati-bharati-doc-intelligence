import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pymupdf as fitz
from PIL import Image

@dataclass
class ParsedPage:
    page_number: int  # 1-indexed
    text: str
    is_scanned: bool = False
    blocks: List[Dict[str, Any]] = None

@dataclass
class DocumentParseResult:
    page_count: int
    pages: List[ParsedPage]
    is_mostly_scanned: bool = False
    file_type: str = "PDF"

class DocumentParserService:
    def parse_document(self, file_path: str, ext: str) -> DocumentParseResult:
        ext = ext.lower().replace(".", "")
        if ext == "pdf":
            return self._parse_pdf(file_path)
        elif ext in ["png", "jpg", "jpeg"]:
            return self._parse_image(file_path, ext)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def _parse_pdf(self, file_path: str) -> DocumentParseResult:
        doc = fitz.open(file_path)
        pages: List[ParsedPage] = []
        total_pages = len(doc)
        scanned_count = 0

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_num = page_idx + 1
            raw_text = page.get_text("text") or ""
            
            # Extract layout blocks
            blocks_raw = page.get_text("blocks")
            blocks = []
            for b in blocks_raw:
                if len(b) >= 5:
                    blocks.append({
                        "bbox": [b[0], b[1], b[2], b[3]],
                        "text": b[4].strip()
                    })

            # If text is extremely short, it's likely a scan or image-based PDF
            is_scanned = len(raw_text.strip()) < 30
            if is_scanned:
                scanned_count += 1

            pages.append(ParsedPage(
                page_number=page_num,
                text=raw_text,
                is_scanned=is_scanned,
                blocks=blocks
            ))

        doc.close()
        is_mostly_scanned = (scanned_count / total_pages) > 0.5 if total_pages > 0 else False

        return DocumentParseResult(
            page_count=total_pages,
            pages=pages,
            is_mostly_scanned=is_mostly_scanned,
            file_type="PDF"
        )

    def _parse_image(self, file_path: str, ext: str) -> DocumentParseResult:
        img = Image.open(file_path)
        # For single image, page count is 1
        return DocumentParseResult(
            page_count=1,
            pages=[
                ParsedPage(
                    page_number=1,
                    text="",  # Extracted via AI Vision or OCR in extraction step
                    is_scanned=True,
                    blocks=[]
                )
            ],
            is_mostly_scanned=True,
            file_type=ext.upper()
        )

    def render_pdf_page_image(self, file_path: str, page_num: int = 1, zoom: float = 1.5) -> bytes:
        """Render a PDF page to PNG bytes for thumbnail / preview"""
        doc = fitz.open(file_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            raise ValueError(f"Page number {page_num} out of range (1-{len(doc)})")
        
        page = doc[page_num - 1]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes

doc_parser_service = DocumentParserService()
