from __future__ import annotations

from pathlib import Path
from typing import Callable

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
        enable_network_search: bool = True,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.local_db_client = local_db_client
        self.pdf_downloader = pdf_downloader
        self.pdf_parser = pdf_parser
        self.chunker = chunker
        self.analyzer = analyzer
        self.value_assessor = value_assessor
        self.network_search_client = network_search_client
        self.enable_network_search = enable_network_search
        self.logger = logger or (lambda message: None)

    def run(self, request: AnalysisRequest) -> FinalReport:
        self.logger(f"[1/7] 拉取本地数据库快照: stock={request.stock_code}, date={request.report_date}")
        snapshot = self.local_db_client.fetch_company_snapshot(request.stock_code, request.report_date)
        return self.run_with_snapshot(request, snapshot)

    def run_with_snapshot(self, request: AnalysisRequest, snapshot) -> FinalReport:
        self.logger(
            f"[1/7] 快照就绪: company={snapshot.company_name}, industry={snapshot.industry}, quarter={snapshot.quarter}"
        )
        self.logger("[2/7] 生成基础中间结论")
        baseline = self.analyzer.analyze_baseline(snapshot)

        self.logger("[3/7] 获取财报 PDF")
        pdf_path = self.pdf_downloader.download(request, snapshot)
        self.logger(f"[3/7] PDF 就绪: path={pdf_path}")

        self.logger("[4/7] 解析 PDF 文本")
        pdf_text = self.pdf_parser.extract_text(pdf_path)
        self.logger(f"[4/7] 文本长度: chars={len(pdf_text)}")

        self.logger("[5/7] 按窗口切块并递进分析")
        chunks = self.chunker.split(pdf_text)
        self.logger(f"[5/7] 切块完成: chunks={len(chunks)}")
        rolling_summary = self.analyzer.analyze_chunks(snapshot, chunks, baseline.summary)

        self.logger("[6/7] 评估当前结果是否具备分析价值")
        initial_assessment = self.value_assessor.assess(rolling_summary)
        self.logger(
            f"[6/7] 价值判断: score={initial_assessment.score}, valuable={initial_assessment.is_valuable}"
        )
        assessment_table = self.analyzer.render_assessment_table(initial_assessment)

        if initial_assessment.is_valuable:
            self.logger("[7/7] 直接生成最终报告，无需网络增强")
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

        if not self.enable_network_search:
            self.logger("[7/7] 已禁用网络检索，基于当前材料直接生成最终报告")
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

        self.logger("[7/7] 当前价值不足，触发网络检索增强")
        search_items = self.network_search_client.search(
            company_name=snapshot.company_name,
            report_date=request.report_date,
            keyword=request.keyword,
        )
        self.logger(f"[7/7] 网络检索完成: items={len(search_items)}")
        enhanced_markdown = self.analyzer.enhance_with_network(snapshot, rolling_summary, search_items)
        final_assessment = self.value_assessor.assess(enhanced_markdown)
        self.logger(
            f"[7/7] 网络增强后价值判断: score={final_assessment.score}, valuable={final_assessment.is_valuable}"
        )
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
