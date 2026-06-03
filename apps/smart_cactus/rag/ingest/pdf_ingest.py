"""
PDF ingestion with OCR support for scanned/image-based PDFs.

Strategy:
  1. Render each page to a high-res image via PyMuPDF (no Poppler needed).
  2. Run EasyOCR (Arabic + English) on the image to extract text.
  3. Chunk text with RecursiveCharacterTextSplitter (500 chars, overlap 100).
  4. Skip chunks shorter than MIN_CHUNK_CHARS.
  5. Section titles detected by heuristic: short lines (≤ 80 chars) that appear
     near the top of the extracted text or are ALL-CAPS / end with a colon.

Fallback: if PyMuPDF / EasyOCR are unavailable, falls back to pdfplumber plain-text
extraction for PDFs that do have selectable text.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 100
_MIN_CHUNK_CHARS = 40
_OCR_DPI = 150  # 150 dpi: good quality, faster than 200 dpi on CPU (A4 = ~1240×1754 px)


class PDFIngestor:
    def __init__(
        self,
        chunk_size: int = _CHUNK_SIZE,
        chunk_overlap: int = _CHUNK_OVERLAP,
        ocr_languages: List[str] = None,
        dpi: int = _OCR_DPI,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "،", " ", ""],
        )
        self._ocr_languages = ocr_languages or ["ar", "en"]
        self._dpi = dpi
        self._reader = None  # lazy-loaded EasyOCR reader

    # ── Public API ────────────────────────────────────────────────────────────

    def load_and_chunk(self, pdf_path: str) -> List[Dict[str, Any]]:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Try OCR pipeline first; fall back to pdfplumber if needed
        try:
            import fitz  # PyMuPDF
            return self._ocr_pipeline(path, fitz)
        except ImportError:
            logger.warning("PyMuPDF not available — falling back to pdfplumber text extraction")
            return self._pdfplumber_pipeline(path)

    # ── OCR pipeline (primary) ────────────────────────────────────────────────

    def _ocr_pipeline(self, path: Path, fitz: Any) -> List[Dict[str, Any]]:
        reader = self._get_ocr_reader()
        chunks: List[Dict[str, Any]] = []
        current_section: Optional[str] = None

        doc = fitz.open(str(path))
        total_pages = len(doc)
        logger.info("OCR pipeline: processing %d pages from %s", total_pages, path.name)

        scale = self._dpi / 72.0  # fitz default is 72 dpi
        mat = fitz.Matrix(scale, scale)

        for page_index in range(total_pages):
            page_num = page_index + 1
            page = doc.load_page(page_index)

            # Render page → RGB numpy array
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
            img_array = self._pixmap_to_numpy(pix)

            # Run OCR
            try:
                ocr_results = reader.readtext(img_array, detail=0, paragraph=True)
                text = "\n".join(ocr_results).strip()
            except Exception as exc:
                logger.warning("OCR failed on page %d: %s", page_num, exc)
                text = ""

            if len(text) < _MIN_CHUNK_CHARS:
                logger.debug("Page %d: OCR produced no usable text, skipping", page_num)
                continue

            if page_num % 10 == 0 or page_num == 1:
                logger.info("Page %d/%d: OCR extracted %d chars", page_num, total_pages, len(text))

            # Detect section title from this page's text
            title = self._detect_section_title(text)
            if title:
                current_section = title

            base_meta = {
                "page_number": page_num,
                "source": path.name,
                "section_title": current_section,
                "element_type": "text",
            }

            for sub in self._splitter.split_text(text):
                sub = sub.strip()
                if len(sub) >= _MIN_CHUNK_CHARS:
                    chunks.append({"content": sub, "metadata": base_meta.copy()})

        doc.close()
        logger.info("OCR pipeline built %d chunks from %d pages", len(chunks), total_pages)
        return chunks

    # ── pdfplumber fallback (for text-based PDFs) ─────────────────────────────

    def _pdfplumber_pipeline(self, path: Path) -> List[Dict[str, Any]]:
        import pdfplumber

        chunks: List[Dict[str, Any]] = []
        current_section: Optional[str] = None

        with pdfplumber.open(str(path)) as pdf:
            total_pages = len(pdf.pages)
            logger.info("pdfplumber pipeline: %d pages from %s", total_pages, path.name)

            for page in pdf.pages:
                page_num = page.page_number
                text = (page.extract_text(x_tolerance=3, y_tolerance=3) or "").strip()
                if len(text) < _MIN_CHUNK_CHARS:
                    continue

                title = self._detect_section_title(text)
                if title:
                    current_section = title

                base_meta = {
                    "page_number": page_num,
                    "source": path.name,
                    "section_title": current_section,
                    "element_type": "text",
                }

                for sub in self._splitter.split_text(text):
                    sub = sub.strip()
                    if len(sub) >= _MIN_CHUNK_CHARS:
                        chunks.append({"content": sub, "metadata": base_meta.copy()})

        logger.info("pdfplumber pipeline built %d chunks", len(chunks))
        return chunks

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_ocr_reader(self) -> Any:
        if self._reader is None:
            import easyocr
            logger.info("Loading EasyOCR model (languages: %s) — first run downloads weights", self._ocr_languages)
            self._reader = easyocr.Reader(self._ocr_languages, gpu=False, verbose=False)
            logger.info("EasyOCR model loaded")
        return self._reader

    @staticmethod
    def _pixmap_to_numpy(pix: Any) -> Any:
        import numpy as np
        samples = pix.samples  # raw bytes: H × W × 3
        arr = np.frombuffer(samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        return arr

    @staticmethod
    def _detect_section_title(text: str) -> Optional[str]:
        """
        Heuristic: first non-empty line ≤ 80 chars that looks like a heading.
        Criteria: all-caps, ends with ':', or is short and followed by a blank line.
        """
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return None

        for line in lines[:5]:  # only look at top 5 lines of the page
            if len(line) < 4 or len(line) > 80:
                continue
            # Arabic or Latin headings: all-caps Latin, or short meaningful line
            is_all_caps = line == line.upper() and re.search(r"[A-Za-z؀-ۿ]", line)
            ends_colon = line.endswith((":", "："))
            is_short = len(line) <= 50
            if is_all_caps or ends_colon or is_short:
                return line

        return None
