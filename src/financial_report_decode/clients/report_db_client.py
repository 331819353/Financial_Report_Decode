from __future__ import annotations

import re
from typing import Any

from financial_report_decode.config import settings
from financial_report_decode.models import PersistedFinancialReport


class ReportDbClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        table: str | None = None,
        timeout: int = 30,
        driver: Any | None = None,
    ) -> None:
        self.host = host or settings.report_db_host
        self.port = port or settings.report_db_port
        self.user = user or settings.report_db_user
        self.password = password or settings.report_db_password
        self.database = database or settings.report_db_name
        self.table = table or settings.report_db_table
        self.timeout = timeout
        self.driver = driver

    def upsert_report(self, report: PersistedFinancialReport) -> None:
        self._validate_config()
        driver = self._load_driver()
        connection = driver.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            connect_timeout=self.timeout,
            charset="utf8mb4",
        )
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                INSERT INTO {self.table}
                (
                    company_code,
                    industry_sector,
                    report_title,
                    year,
                    quarter,
                    report_type,
                    company_name,
                    summary
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    industry_sector = VALUES(industry_sector),
                    report_title = VALUES(report_title),
                    company_name = VALUES(company_name),
                    summary = VALUES(summary)
                """,
                (
                    report.company_code,
                    report.industry,
                    report.report_title,
                    report.year,
                    report.quarter,
                    report.report_type,
                    report.company_name,
                    report.summary,
                ),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _validate_config(self) -> None:
        missing_fields = [
            field_name
            for field_name, value in (
                ("host", self.host),
                ("user", self.user),
                ("password", self.password),
                ("database", self.database),
                ("table", self.table),
            )
            if not value
        ]
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise ValueError(f"Report DB config is incomplete: {fields}")
        if not re.fullmatch(r"[A-Za-z0-9_]+", self.table):
            raise ValueError("Report DB table contains invalid characters")

    def _load_driver(self) -> Any:
        if self.driver is not None:
            return self.driver
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError("pymysql is required for report database writes") from exc
        return pymysql
