from __future__ import annotations

import argparse
from pathlib import Path

from financial_report_decode.clients.llm_client import LlmClient
from financial_report_decode.clients.local_db_client import LocalDbClient
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
    parser.add_argument("--stock", required=True, help="股票编码，例如 002508.SZ")
    parser.add_argument("--date", required=True, help="财报日期，例如 2025-06-30")
    parser.add_argument("--keyword", default="营业收入", help="网络检索关键字")
    parser.add_argument("--pdf-url", default=None, help="财报 PDF 直链，可选")
    parser.add_argument("--output", default=settings.reports_dir, help="输出目录")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    request = AnalysisRequest(
        stock_code=args.stock,
        report_date=args.date,
        keyword=args.keyword,
        pdf_url=args.pdf_url,
    )

    orchestrator = FinancialReportOrchestrator(
        local_db_client=LocalDbClient(),
        pdf_downloader=PdfDownloader(),
        pdf_parser=PdfParser(),
        chunker=ContextualChunker(),
        analyzer=ReportAnalyzer(LlmClient()),
        value_assessor=ReportValueAssessor(),
        network_search_client=NetworkSearchClient(),
    )

    final_report = orchestrator.run(request)
    filename = f"{args.stock}_{args.date}_analysis.md"
    output_path = orchestrator.write_report(final_report.markdown, Path(args.output), filename)
    print(f"Report written to: {output_path}")
    print(f"Web enhanced: {final_report.is_web_enhanced}")
    print(f"Value score: {final_report.value_assessment.score}")


if __name__ == "__main__":
    main()

