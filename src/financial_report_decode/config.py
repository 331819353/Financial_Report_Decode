from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    local_db_url: str = os.getenv(
        "LOCAL_DB_URL",
        "http://hgpmp.haier.net/cgapi3/company-data/basic-data-ai",
    )
    network_search_url: str = os.getenv(
        "NETWORK_SEARCH_URL",
        "https://cloud-iqs.aliyuncs.com/search/unified",
    )
    network_search_token: str = os.getenv("ALIYUN_IQS_BEARER_TOKEN", "")
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    dashscope_base_url: str = os.getenv(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    llm_model: str = os.getenv("LLM_MODEL", "qwen3.5-plus")
    llm_enable_thinking: bool = os.getenv("LLM_ENABLE_THINKING", "true").lower() == "true"
    pdf_download_endpoint: str = os.getenv(
        "PDF_DOWNLOAD_ENDPOINT",
        "https://hgpmp.haier.net/cgapi3/dmzlyyextinfo/downFile",
    )
    pdf_download_url_template: str = os.getenv("PDF_DOWNLOAD_URL_TEMPLATE", "")
    pdf_download_timeout: int = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "60"))
    network_retrieve_max_items: int = int(os.getenv("NETWORK_RETRIEVE_MAX_ITEMS", "5"))
    reports_dir: str = os.getenv("REPORTS_DIR", "reports")
    downloads_dir: str = os.getenv("DOWNLOADS_DIR", "downloads")


settings = Settings()
