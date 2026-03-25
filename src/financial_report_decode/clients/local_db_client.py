from __future__ import annotations

import requests

from financial_report_decode.config import settings
from financial_report_decode.models import LocalMetricSnapshot


class LocalDbClient:
    def __init__(self, base_url: str | None = None, timeout: int = 30) -> None:
        self.base_url = base_url or settings.local_db_url
        self.timeout = timeout

    def fetch_company_snapshot(self, stock_code: str, report_date: str) -> LocalMetricSnapshot:
        response = requests.get(
            self.base_url,
            params={"stockCode": stock_code, "reportDate": report_date},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or []
        if not data:
            raise ValueError(f"Local DB returned empty data for {stock_code} @ {report_date}")

        filtered = {key: value for key, value in data[0].items() if value != ""}
        company_name = filtered.get("公司名", "")
        industry = filtered.get("子行业", "")
        year = report_date[:4]
        quarter = self._quarter_from_date(report_date)
        report_title = f"{company_name}_{year}{quarter}_财务报告.pdf"

        return LocalMetricSnapshot(
            industry=industry,
            year=year,
            quarter=quarter,
            company_name=company_name,
            report_title=report_title,
            metrics=filtered,
        )

    @staticmethod
    def _quarter_from_date(report_date: str) -> str:
        suffix = report_date[4:]
        if suffix == "-03-31":
            return "Q1"
        if suffix == "-06-30":
            return "H1"
        if suffix == "-09-30":
            return "Q3"
        return "FY"

