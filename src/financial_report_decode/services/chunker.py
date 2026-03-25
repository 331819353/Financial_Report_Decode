from __future__ import annotations

from financial_report_decode.models import PdfChunk


class ContextualChunker:
    def __init__(self, core_size: int = 20000, context_size: int = 1000) -> None:
        self.core_size = core_size
        self.context_size = context_size

    def split(self, text: str) -> list[PdfChunk]:
        chunks: list[PdfChunk] = []
        start = 0
        chunk_id = 1
        text_length = len(text)

        while start < text_length:
            core_end = min(start + self.core_size, text_length)
            chunk_start = max(start - self.context_size, 0)
            chunk_end = min(core_end + self.context_size, text_length)
            chunks.append(
                PdfChunk(
                    chunk_id=chunk_id,
                    text=text[chunk_start:chunk_end],
                    start=chunk_start,
                    end=chunk_end,
                )
            )
            start = core_end
            chunk_id += 1

        return chunks

