from __future__ import annotations

from pathlib import Path

from financial_report_decode.clients.local_db_client import LocalDbClient
from financial_report_decode.clients.network_search_client import NetworkSearchClient
from financial_report_decode.clients.pdf_client import PdfDownloader
from financial_report_decode.models import AnalysisRequest, FinalReport
from financial_report_decode.services.chunker import ContextualChunker
from financial_report_decode.services.pdf_parser import PdfParser
from financial_report_decode.services.report_analyzer import ReportAnalyzer
from financial_report_decode.services.report_value import ReportValueAssessor


class FinancialReportOrchestrator:
    def __init__(
        self,
        local_db_client: LocalDbClient,
        pdf_downloader: PdfDownloader,
        pdf_parser: PdfParser,
        chunker: ContextualChunker,
        analyzer: ReportAnalyzer,
        value_assessor: ReportValueAssessor,
        network_search_client: NetworkSearchClient,
    ) -> None:
        self.local_db_client = local_db_client
        self.pdf_downloader = pdf_downloader
        self.pdf_parser = pdf_parser
        self.chunker = chunker
        self.analyzer = analyzer
        self.value_assessor = value_assessor
        self.network_search_client = network_search_client

    def run(self, request: AnalysisRequest) -> FinalReport:
        snapshot = self.local_db_client.fetch_company_snapshot(request.stock_code, request.report_date)
        baseline = self.analyzer.analyze_baseline(snapshot)

        pdf_path = self.pdf_downloader.download(request, snapshot)
        pdf_text = self.pdf_parser.extract_text(pdf_path)
        chunks = self.chunker.split(pdf_text)
        rolling_summary = self.analyzer.analyze_chunks(snapshot, chunks, baseline.summary)

        initial_assessment = self.value_assessor.assess(rolling_summary)
        assessment_table = self.analyzer.render_assessment_table(initial_assessment)

        if initial_assessment.is_valuable:
            markdown = self.analyzer.render_final_without_network(
                snapshot=snapshot,
                summary=rolling_summary,
                assessment_markdown=assessment_table,
            )
            return FinalReport(
                markdown=markdown,
                is_web_enhanced=False,
                value_assessment=initial_assessment,
            )

        search_items = self.network_search_client.search(
            company_name=snapshot.company_name,
            report_date=request.report_date,
            keyword=request.keyword,
        )
        enhanced_markdown = self.analyzer.enhance_with_network(snapshot, rolling_summary, search_items)
        final_assessment = self.value_assessor.assess(enhanced_markdown)
        return FinalReport(
            markdown=enhanced_markdown,
            is_web_enhanced=True,
            value_assessment=final_assessment,
        )

    @staticmethod
    def write_report(markdown: str, output_dir: str | Path, filename: str) -> Path:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        path.write_text(markdown, encoding="utf-8")
        return path

