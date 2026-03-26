from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from financial_report_decode.clients.llm_client import LlmClient
from financial_report_decode.clients.local_db_client import LocalDbClient
from financial_report_decode.clients.mock_llm_client import MockLlmClient
from financial_report_decode.clients.network_search_client import NetworkSearchClient
from financial_report_decode.clients.pdf_client import PdfDownloader
from financial_report_decode.clients.report_db_client import ReportDbClient
from financial_report_decode.config import settings
from financial_report_decode.models import (
    AnalysisRequest,
    FinalReport,
    LocalMetricSnapshot,
    PersistedFinancialReport,
    ReportBundle,
)
from financial_report_decode.services.chunker import ContextualChunker
from financial_report_decode.services.orchestrator import FinancialReportOrchestrator
from financial_report_decode.services.pdf_parser import PdfParser
from financial_report_decode.services.report_analyzer import ReportAnalyzer
from financial_report_decode.services.report_value import BriefReportAssessor, ReportValueAssessor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Financial report decode pipeline")
    parser.add_argument("--stock", required=True, help="正式必填入参：股票编码，例如 002508.SZ")
    parser.add_argument("--date", required=True, help="正式必填入参：财报日期，例如 2025-06-30")
    parser.add_argument("--keyword", default="营业收入", help="网络检索关键字")
    parser.add_argument("--pdf-url", default=None, help="调试参数：财报 PDF 直链，可选")
    parser.add_argument("--pdf-path", default=None, help="调试参数：本地 PDF 文件路径")
    parser.add_argument("--snapshot-file", default=None, help="调试参数：本地数据库结果 JSON 文件")
    parser.add_argument("--mock-llm", action="store_true", help="调试参数：使用 mock LLM")
    parser.add_argument("--skip-network-search", action="store_true", help="调试参数：跳过网络检索")
    parser.add_argument("--show-logs", action="store_true", help="输出每一步执行日志")
    parser.add_argument("--output", default=settings.reports_dir, help="输出目录")
    return parser


def build_logger(enabled: bool):
    def log(message: str) -> None:
        if enabled:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] {message}", flush=True)

    return log


def configure_streams_for_live_logs(enabled: bool) -> None:
    if not enabled:
        return

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(line_buffering=True, write_through=True)


def build_orchestrator(
    local_db_client: LocalDbClient,
    mock_llm: bool,
    skip_network_search: bool,
    logger,
) -> FinancialReportOrchestrator:
    llm_client = MockLlmClient() if mock_llm else LlmClient()
    return FinancialReportOrchestrator(
        local_db_client=local_db_client,
        pdf_downloader=PdfDownloader(),
        pdf_parser=PdfParser(),
        chunker=ContextualChunker(),
        analyzer=ReportAnalyzer(llm_client),
        value_assessor=ReportValueAssessor(),
        brief_value_assessor=BriefReportAssessor(),
        network_search_client=NetworkSearchClient(),
        enable_network_search=not skip_network_search,
        logger=logger,
    )


def load_snapshot(
    local_db_client: LocalDbClient,
    request: AnalysisRequest,
    snapshot_file: str | None,
    logger,
) -> LocalMetricSnapshot:
    if snapshot_file:
        logger(f"[0/7] 使用本地快照文件: {snapshot_file}")
        snapshot_payload = json.loads(Path(snapshot_file).read_text(encoding="utf-8"))
        return local_db_client.build_snapshot_from_payload(snapshot_payload, request.report_date)

    logger(f"[1/7] 拉取本地数据库快照: stock={request.stock_code}, date={request.report_date}")
    return local_db_client.fetch_company_snapshot(request.stock_code, request.report_date)


def run_pipeline(
    request: AnalysisRequest,
    snapshot_file: str | None,
    mock_llm: bool,
    skip_network_search: bool,
    logger,
) -> tuple[LocalMetricSnapshot, ReportBundle]:
    local_db_client = LocalDbClient()
    orchestrator = build_orchestrator(
        local_db_client=local_db_client,
        mock_llm=mock_llm,
        skip_network_search=skip_network_search,
        logger=logger,
    )
    snapshot = load_snapshot(local_db_client, request, snapshot_file, logger)
    final_report = orchestrator.run_with_snapshot(request, snapshot)
    return snapshot, final_report


def build_persisted_report(
    request: AnalysisRequest,
    snapshot: LocalMetricSnapshot,
    final_report: FinalReport,
    overrides: dict[str, Any] | None = None,
) -> PersistedFinancialReport:
    payload = overrides or {}
    quarter = str(payload.get("quarter") or snapshot.quarter)
    return PersistedFinancialReport(
        company_code=str(payload.get("company_code") or request.stock_code),
        industry=str(payload.get("industry") or snapshot.industry),
        summary=str(payload.get("summary") or final_report.markdown),
        company_name=str(payload.get("company_name") or snapshot.company_name),
        report_type=str(payload.get("report_type") or "DR"),
        quarter=quarter,
        year=str(payload.get("year") or snapshot.year),
        report_title=str(payload.get("report_title") or snapshot.report_title),
    )


def build_report_title(snapshot: LocalMetricSnapshot, report_type: str) -> str:
    title = snapshot.report_title.rsplit(".", 1)[0]
    extension = snapshot.report_title.rsplit(".", 1)[1] if "." in snapshot.report_title else ""
    suffix = f"_{report_type}"
    if title.endswith(suffix):
        return snapshot.report_title
    return f"{title}{suffix}.{extension}" if extension else f"{title}{suffix}"


def build_report_db_client(overrides: dict[str, Any] | None = None) -> ReportDbClient:
    payload = overrides or {}
    port_value = payload.get("report_db_port") or payload.get("db_port")
    return ReportDbClient(
        host=payload.get("report_db_host") or payload.get("db_host"),
        port=int(port_value) if port_value else None,
        user=payload.get("report_db_user") or payload.get("db_user"),
        password=payload.get("report_db_password") or payload.get("db_password"),
        database=payload.get("report_db_name") or payload.get("db_name"),
        table=payload.get("report_db_table") or payload.get("db_table"),
    )


def write_report_artifact(
    request: AnalysisRequest,
    final_report: FinalReport,
    output_dir: str | Path,
    report_type: str,
) -> Path:
    filename = f"{request.stock_code}_{request.report_date}_{report_type.lower()}_analysis.md"
    return FinancialReportOrchestrator.write_report(final_report.markdown, Path(output_dir), filename)


def require_param(params: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = params.get(key)
        if value not in (None, ""):
            return str(value)
    aliases = ", ".join(keys)
    raise ValueError(f"Missing required parameter: {aliases}")


def build_request_from_params(params: dict[str, Any]) -> AnalysisRequest:
    return AnalysisRequest(
        stock_code=require_param(params, "company_code", "stock_code", "stock"),
        report_date=require_param(params, "report_date", "date"),
        keyword=str(params.get("keyword") or "营业收入"),
        pdf_url=params.get("pdf_url"),
        pdf_path=params.get("pdf_path"),
    )


def handler(params: dict[str, Any]) -> dict[str, Any]:
    show_logs = bool(params.get("show_logs", False))
    configure_streams_for_live_logs(show_logs)
    logger = build_logger(show_logs)

    if params.get("summary") and not any(params.get(key) for key in ("report_date", "date")):
        persisted_report = PersistedFinancialReport(
            company_code=require_param(params, "company_code", "stock_code", "stock"),
            industry=require_param(params, "industry"),
            summary=require_param(params, "summary"),
            company_name=require_param(params, "company_name"),
            report_type=require_param(params, "report_type"),
            quarter=require_param(params, "quarter"),
            year=require_param(params, "year"),
            report_title=require_param(params, "report_title"),
        )
        build_report_db_client(params).upsert_report(persisted_report)
        return {"result": "数据已成功写入数据库"}

    request = build_request_from_params(params)
    snapshot, report_bundle = run_pipeline(
        request=request,
        snapshot_file=params.get("snapshot_file"),
        mock_llm=bool(params.get("mock_llm", False)),
        skip_network_search=bool(params.get("skip_network_search", False)),
        logger=logger,
    )
    detail_output_path = write_report_artifact(
        request=request,
        final_report=report_bundle.detailed_report,
        output_dir=params.get("output") or settings.reports_dir,
        report_type="DR",
    )
    brief_output_path = write_report_artifact(
        request=request,
        final_report=report_bundle.brief_report,
        output_dir=params.get("output") or settings.reports_dir,
        report_type="BR",
    )
    db_client = build_report_db_client(params)
    detail_persisted_report = build_persisted_report(
        request,
        snapshot,
        report_bundle.detailed_report,
        {
            **params,
            "report_type": "DR",
            "report_title": build_report_title(snapshot, "DR"),
        },
    )
    brief_persisted_report = build_persisted_report(
        request,
        snapshot,
        report_bundle.brief_report,
        {
            **params,
            "report_type": "BR",
            "report_title": build_report_title(snapshot, "BR"),
        },
    )
    db_client.upsert_report(detail_persisted_report)
    db_client.upsert_report(brief_persisted_report)
    return {
        "result": "详报与简报已成功写入数据库",
        "detail_output_path": str(detail_output_path),
        "brief_output_path": str(brief_output_path),
        "web_enhanced": report_bundle.detailed_report.is_web_enhanced,
        "detail_value_score": report_bundle.detailed_report.value_assessment.score,
        "brief_value_score": report_bundle.brief_report.value_assessment.score,
    }


def main() -> None:
    args = build_parser().parse_args()
    configure_streams_for_live_logs(args.show_logs)
    logger = build_logger(args.show_logs)
    request = AnalysisRequest(
        stock_code=args.stock,
        report_date=args.date,
        keyword=args.keyword,
        pdf_url=args.pdf_url,
        pdf_path=args.pdf_path,
    )
    snapshot, report_bundle = run_pipeline(
        request=request,
        snapshot_file=args.snapshot_file,
        mock_llm=args.mock_llm,
        skip_network_search=args.skip_network_search,
        logger=logger,
    )
    logger("[7/9] 写入详报与简报文件")
    detail_output_path = write_report_artifact(request, report_bundle.detailed_report, args.output, "DR")
    brief_output_path = write_report_artifact(request, report_bundle.brief_report, args.output, "BR")
    logger("[8/9] 写入详报与简报数据库")
    db_client = build_report_db_client()
    db_client.upsert_report(
        build_persisted_report(
            request,
            snapshot,
            report_bundle.detailed_report,
            {"report_type": "DR", "report_title": build_report_title(snapshot, "DR")},
        )
    )
    db_client.upsert_report(
        build_persisted_report(
            request,
            snapshot,
            report_bundle.brief_report,
            {"report_type": "BR", "report_title": build_report_title(snapshot, "BR")},
        )
    )
    print(f"Detailed report written to: {detail_output_path}")
    print(f"Brief report written to: {brief_output_path}")
    print("DB write: success")
    print(f"Web enhanced: {report_bundle.detailed_report.is_web_enhanced}")
    print(f"Detailed value score: {report_bundle.detailed_report.value_assessment.score}")
    print(f"Brief value score: {report_bundle.brief_report.value_assessment.score}")


if __name__ == "__main__":
    main()
