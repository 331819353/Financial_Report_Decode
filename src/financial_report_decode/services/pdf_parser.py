from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


class PdfParser:
    def extract_text(self, pdf_path: str | Path) -> str:
        reader = PdfReader(str(pdf_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text.strip())
        combined = "\n\n".join(part for part in pages if part)
        if not combined.strip():
            raise ValueError(f"No extractable text found in PDF: {pdf_path}")
        return combined

