from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from financial_report_decode.clients.llm_client import LlmClient
from financial_report_decode.clients.local_db_client import LocalDbClient
from financial_report_decode.clients.mock_llm_client import MockLlmClient
from financial_report_decode.clients.network_search_client import NetworkSearchClient
from financial_report_decode.clients.pdf_client import PdfDownloader
from financial_report_decode.config import settings
from financial_report_decode.models import AnalysisRequest
from financial_report_decode.services.chunker import ContextualChunker
from financial_report_decode.services.orchestrator import FinancialReportOrchestrator
from financial_report_decode.services.pdf_parser import PdfParser
from financial_report_decode.services.report_analyzer import ReportAnalyzer
from financial_report_decode.services.report_value import ReportValueAssessor


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


def main() -> None:
    args = build_parser().parse_args()
    configure_streams_for_live_logs(args.show_logs)
    request = AnalysisRequest(
        stock_code=args.stock,
        report_date=args.date,
        keyword=args.keyword,
        pdf_url=args.pdf_url,
        pdf_path=args.pdf_path,
    )

    local_db_client = LocalDbClient()
    llm_client = MockLlmClient() if args.mock_llm else LlmClient()
    logger = build_logger(args.show_logs)

    orchestrator = FinancialReportOrchestrator(
        local_db_client=local_db_client,
        pdf_downloader=PdfDownloader(),
        pdf_parser=PdfParser(),
        chunker=ContextualChunker(),
        analyzer=ReportAnalyzer(llm_client),
        value_assessor=ReportValueAssessor(),
        network_search_client=NetworkSearchClient(),
        enable_network_search=not args.skip_network_search,
        logger=logger,
    )

    if args.snapshot_file:
        logger(f"[0/7] 使用本地快照文件: {args.snapshot_file}")
        snapshot_payload = json.loads(Path(args.snapshot_file).read_text(encoding="utf-8"))
        snapshot = local_db_client.build_snapshot_from_payload(snapshot_payload, args.date)
        final_report = orchestrator.run_with_snapshot(request, snapshot)
    else:
        final_report = orchestrator.run(request)

    filename = f"{args.stock}_{args.date}_analysis.md"
    logger(f"[7/7] 写入最终报告: {filename}")
    output_path = orchestrator.write_report(final_report.markdown, Path(args.output), filename)
    print(f"Report written to: {output_path}")
    print(f"Web enhanced: {final_report.is_web_enhanced}")
    print(f"Value score: {final_report.value_assessment.score}")


if __name__ == "__main__":
    main()
