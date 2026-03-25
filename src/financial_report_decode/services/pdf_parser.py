from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import fitz
from pypdf import PdfReader
from PIL import Image

from financial_report_decode.config import settings


class PdfParser:
    def __init__(
        self,
        ocr_enabled: bool | None = None,
        ocr_dpi: int | None = None,
        min_text_length: int | None = None,
        garbled_ratio_threshold: float | None = None,
    ) -> None:
        self.ocr_enabled = settings.pdf_ocr_enabled if ocr_enabled is None else ocr_enabled
        self.ocr_dpi = settings.pdf_ocr_dpi if ocr_dpi is None else ocr_dpi
        self.min_text_length = (
            settings.pdf_text_min_length if min_text_length is None else min_text_length
        )
        self.garbled_ratio_threshold = (
            settings.pdf_garbled_char_ratio_threshold
            if garbled_ratio_threshold is None
            else garbled_ratio_threshold
        )
        self._rapid_ocr_engine = None

    def extract_text(self, pdf_path: str | Path) -> str:
        extracted_text = self._extract_text_with_pypdf(pdf_path)
        if self._should_use_ocr(extracted_text):
            ocr_text = self._extract_text_with_ocr(pdf_path)
            if ocr_text.strip() and self._text_quality_score(ocr_text) >= self._text_quality_score(
                extracted_text
            ):
                return ocr_text
        if not extracted_text.strip():
            raise ValueError(f"No extractable text found in PDF: {pdf_path}")
        return extracted_text

    def _extract_text_with_pypdf(self, pdf_path: str | Path) -> str:
        reader = PdfReader(str(pdf_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text.strip())
        return "\n\n".join(part for part in pages if part)

    def _extract_text_with_ocr(self, pdf_path: str | Path) -> str:
        pages: list[str] = []
        document = fitz.open(str(pdf_path))
        try:
            for page in document:
                pix = page.get_pixmap(dpi=self.ocr_dpi, alpha=False)
                image = Image.open(BytesIO(pix.tobytes("png")))
                lines = self._recognize_image(image)
                pages.append("\n".join(lines))
        finally:
            document.close()
        return "\n\n".join(part for part in pages if part)

    def _recognize_image(self, image: Image.Image) -> list[str]:
        rapid_lines = self._recognize_with_rapidocr(image)
        if rapid_lines:
            return rapid_lines
        return self._recognize_with_ocrmac(image)

    def _recognize_with_rapidocr(self, image: Image.Image) -> list[str]:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except Exception:
            return []

        if self._rapid_ocr_engine is None:
            self._rapid_ocr_engine = RapidOCR()

        image_array = self._pil_to_ndarray(image)
        ocr_result, _ = self._rapid_ocr_engine(
            image_array,
            use_det=True,
            use_cls=True,
            use_rec=True,
        )
        lines = []
        for item in ocr_result or []:
            text = item[1] if len(item) > 1 else ""
            if text:
                lines.append(text.strip())
        return lines

    @staticmethod
    def _recognize_with_ocrmac(image: Image.Image) -> list[str]:
        try:
            from ocrmac.ocrmac import OCR
        except Exception as exc:
            raise RuntimeError(
                "OCR backend unavailable. Install rapidocr-onnxruntime or ocrmac."
            ) from exc

        result = OCR(
            image,
            framework="vision",
            recognition_level="accurate",
            language_preference=["zh-Hans", "zh-Hant", "en-US"],
            detail=False,
        ).recognize()
        lines = []
        for item in result:
            text = item.strip() if isinstance(item, str) else ""
            if text:
                lines.append(text)
        return lines

    def _should_use_ocr(self, text: str) -> bool:
        if not self.ocr_enabled:
            return False
        clean_text = text.strip()
        if not clean_text:
            return True
        if len(clean_text) < self.min_text_length:
            return True
        return self._garbled_char_ratio(clean_text) >= self.garbled_ratio_threshold

    @staticmethod
    def _garbled_char_ratio(text: str) -> float:
        suspicious_chars = re.findall(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u0370-\u03ff\u0b80-\u0bff\u0c80-\u0cff\ufffd]",
            text,
        )
        return len(suspicious_chars) / max(len(text), 1)

    def _text_quality_score(self, text: str) -> float:
        clean_text = text.strip()
        if not clean_text:
            return 0.0
        suspicious_ratio = self._garbled_char_ratio(clean_text)
        valid_chars = re.findall(
            r"[\u4e00-\u9fffA-Za-z0-9，。；：！？、“”‘’（）()【】《》\[\]\-—%.,:;/+&\s]",
            clean_text,
        )
        valid_ratio = len(valid_chars) / max(len(clean_text), 1)
        length_score = min(len(clean_text) / 10000, 1.0)
        return valid_ratio * 0.6 + (1 - suspicious_ratio) * 0.3 + length_score * 0.1

    @staticmethod
    def _pil_to_ndarray(image: Image.Image):
        import numpy as np

        return np.array(image)
