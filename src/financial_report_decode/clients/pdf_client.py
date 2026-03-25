from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import requests

from financial_report_decode.config import settings
from financial_report_decode.models import AnalysisRequest, LocalMetricSnapshot


class PdfDownloader:
    def __init__(self, timeout: int | None = None) -> None:
        self.timeout = timeout or settings.pdf_download_timeout

    def download(
        self,
        request: AnalysisRequest,
        snapshot: LocalMetricSnapshot,
        output_dir: str | Path | None = None,
    ) -> Path:
        url = request.pdf_url or self._build_url(request, snapshot)
        if not url:
            raise ValueError(
                "No PDF URL available. Provide --pdf-url or configure PDF_DOWNLOAD_URL_TEMPLATE."
            )

        target_dir = Path(output_dir or settings.downloads_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / snapshot.report_title

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        return target_path

    def _build_url(self, request: AnalysisRequest, snapshot: LocalMetricSnapshot) -> str:
        template = settings.pdf_download_url_template
        if not template:
            return ""

        substitutions = {
            "stock_code": request.stock_code,
            "report_date": request.report_date,
            "year": snapshot.year,
            "quarter": snapshot.quarter,
            "company_name": quote(snapshot.company_name),
            "report_title": quote(snapshot.report_title),
        }
        return template.format(**substitutions)

