from __future__ import annotations

import requests

from financial_report_decode.config import settings
from financial_report_decode.models import NetworkSearchItem


class NetworkSearchClient:
    def __init__(self, token: str | None = None, base_url: str | None = None, timeout: int = 30) -> None:
        self.token = token or settings.network_search_token
        self.base_url = base_url or settings.network_search_url
        self.timeout = timeout

    def search(self, company_name: str, report_date: str, keyword: str) -> list[NetworkSearchItem]:
        if not self.token:
            raise ValueError("ALIYUN_IQS_BEARER_TOKEN is required for network search")

        year_num = report_date[:4]
        quarter_num = self._quarter_num(report_date)
        query = f"{company_name}累计到{year_num}年第{quarter_num}季度的{keyword}是多少？"

        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "engineType": "Generic",
                "contents": {
                    "mainText": True,
                    "markdownText": False,
                    "summary": True,
                    "rerankScore": True,
                },
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        result = []
        page_items = response.json().get("pageItems") or []
        for page_item in page_items[: settings.network_retrieve_max_items]:
            result.append(
                NetworkSearchItem(
                    source=page_item.get("link", ""),
                    content=page_item.get("mainText", ""),
                )
            )
        return result

    @staticmethod
    def _quarter_num(report_date: str) -> int:
        if "03-31" in report_date:
            return 1
        if "06-30" in report_date:
            return 2
        if "09-30" in report_date:
            return 3
        if "12-31" in report_date:
            return 4
        return 1

