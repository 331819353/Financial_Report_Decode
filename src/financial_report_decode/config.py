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
    llm_api_key: str = os.getenv("LLM_API_KEY") or os.getenv("MGALLERY_API_KEY") or os.getenv(
        "DASHSCOPE_API_KEY", ""
    )
    llm_base_url: str = os.getenv("LLM_BASE_URL") or os.getenv(
        "MGALLERY_BASE_URL",
        "https://mgallery.haier.net/v1",
    )
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-v3")
    llm_enable_thinking: bool = os.getenv("LLM_ENABLE_THINKING", "true").lower() == "true"
    pdf_download_endpoint: str = os.getenv(
        "PDF_DOWNLOAD_ENDPOINT",
        "https://hgpmp.haier.net/cgapi3/dmzlyyextinfo/downFile",
    )
    pdf_download_url_template: str = os.getenv("PDF_DOWNLOAD_URL_TEMPLATE", "")
    pdf_download_timeout: int = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "60"))
    network_retrieve_max_items: int = int(os.getenv("NETWORK_RETRIEVE_MAX_ITEMS", "3"))
    reports_dir: str = os.getenv("REPORTS_DIR", "reports")
    downloads_dir: str = os.getenv("DOWNLOADS_DIR", "downloads")
    pdf_ocr_enabled: bool = os.getenv("PDF_OCR_ENABLED", "true").lower() == "true"
    pdf_ocr_dpi: int = int(os.getenv("PDF_OCR_DPI", "200"))
    pdf_text_min_length: int = int(os.getenv("PDF_TEXT_MIN_LENGTH", "2000"))
    pdf_garbled_char_ratio_threshold: float = float(
        os.getenv("PDF_GARBLED_CHAR_RATIO_THRESHOLD", "0.04")
    )
    pdf_ocr_languages: str = os.getenv("PDF_OCR_LANGUAGES", "zh-Hans,zh-Hant,en-US")
    pdf_tesseract_lang: str = os.getenv("PDF_TESSERACT_LANG", "chi_sim+chi_tra+eng")
    pdf_tesseract_cmd: str = os.getenv("PDF_TESSERACT_CMD", "")
    network_enhance_max_rounds: int = int(os.getenv("NETWORK_ENHANCE_MAX_ROUNDS", "3"))
    report_db_host: str = os.getenv("REPORT_DB_HOST", "")
    report_db_port: int = int(os.getenv("REPORT_DB_PORT", "3306"))
    report_db_user: str = os.getenv("REPORT_DB_USER", "")
    report_db_password: str = os.getenv("REPORT_DB_PASSWORD", "")
    report_db_name: str = os.getenv("REPORT_DB_NAME", "")
    report_db_table: str = os.getenv("REPORT_DB_TABLE", "caibao_financial_reports")


settings = Settings()
