from __future__ import annotations

import json

import requests

from financial_report_decode.config import settings
from financial_report_decode.models import LocalMetricSnapshot, snapshot_company_name, snapshot_industry


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
        return self._build_snapshot(filtered, report_date)

    def build_snapshot_from_payload(self, payload: dict, report_date: str) -> LocalMetricSnapshot:
        raw_result = payload.get("result", "{}")
        metrics = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
        filtered = {key: value for key, value in metrics.items() if value != ""}
        company_name = str(payload.get("company_name") or snapshot_company_name(filtered))
        industry = str(payload.get("industry") or snapshot_industry(filtered))
        return LocalMetricSnapshot(
            industry=industry,
            year=payload.get("year", report_date[:4]),
            quarter=payload.get("quarter", self._quarter_from_date(report_date)),
            company_name=company_name,
            report_title=payload.get(
                "report_title",
                f"{company_name}_{report_date[:4]}{self._quarter_from_date(report_date)}_财务报告.pdf",
            ),
            metrics=filtered,
        )

    def _build_snapshot(self, filtered: dict, report_date: str) -> LocalMetricSnapshot:
        company_name = snapshot_company_name(filtered)
        industry = snapshot_industry(filtered)
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
