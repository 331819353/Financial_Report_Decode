from __future__ import annotations

from pathlib import Path
from typing import Callable

from financial_report_decode.config import settings
from financial_report_decode.clients.local_db_client import LocalDbClient
from financial_report_decode.clients.network_search_client import NetworkSearchClient
from financial_report_decode.clients.pdf_client import PdfDownloader
from financial_report_decode.models import AnalysisRequest, FinalReport, NetworkSearchItem, ReportBundle
from financial_report_decode.services.chunker import ContextualChunker
from financial_report_decode.services.pdf_parser import PdfParser
from financial_report_decode.services.report_analyzer import ReportAnalyzer
from financial_report_decode.services.report_value import BriefReportAssessor, ReportValueAssessor


class FinancialReportOrchestrator:
    def __init__(
        self,
        local_db_client: LocalDbClient,
        pdf_downloader: PdfDownloader,
        pdf_parser: PdfParser,
        chunker: ContextualChunker,
        analyzer: ReportAnalyzer,
        value_assessor: ReportValueAssessor,
        brief_value_assessor: BriefReportAssessor,
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
        self.brief_value_assessor = brief_value_assessor
        self.network_search_client = network_search_client
        self.enable_network_search = enable_network_search
        self.logger = logger or (lambda message: None)

    def run(self, request: AnalysisRequest) -> ReportBundle:
        self.logger(f"[1/7] 拉取本地数据库快照: stock={request.stock_code}, date={request.report_date}")
        snapshot = self.local_db_client.fetch_company_snapshot(request.stock_code, request.report_date)
        return self.run_with_snapshot(request, snapshot)

    def run_with_snapshot(self, request: AnalysisRequest, snapshot) -> ReportBundle:
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
            detailed_report = FinalReport(
                markdown=markdown,
                is_web_enhanced=False,
                value_assessment=initial_assessment,
            )
            brief_report = self._build_brief_report(snapshot, detailed_report, [])
            return ReportBundle(detailed_report=detailed_report, brief_report=brief_report)

        if not self.enable_network_search:
            self.logger("[7/7] 已禁用网络检索，基于当前材料直接生成最终报告")
            markdown = self.analyzer.render_final_without_network(
                snapshot=snapshot,
                summary=rolling_summary,
                assessment_markdown=assessment_table,
            )
            detailed_report = FinalReport(
                markdown=markdown,
                is_web_enhanced=False,
                value_assessment=initial_assessment,
            )
            brief_report = self._build_brief_report(snapshot, detailed_report, [])
            return ReportBundle(detailed_report=detailed_report, brief_report=brief_report)

        self.logger("[7/7] 当前价值不足，触发网络检索增强")
        aggregated_items: list[NetworkSearchItem] = []
        asked_queries: list[str] = []
        final_markdown = ""
        final_assessment = initial_assessment

        for round_no in range(1, settings.network_enhance_max_rounds + 1):
            queries = self.analyzer.build_network_queries(
                snapshot=snapshot,
                current_summary=rolling_summary,
                missing_dimensions=final_assessment.missing_dimensions,
                asked_queries=asked_queries,
            )
            if not queries:
                self.logger(f"[7/7] 第 {round_no} 轮未生成新的检索问题，结束增强")
                break

            self.logger(f"[7/7] 第 {round_no} 轮检索问题: {' | '.join(queries)}")
            round_items: list[NetworkSearchItem] = []
            for query in queries:
                asked_queries.append(query)
                items = self.network_search_client.search_by_query(query)
                round_items.extend(items)
                self.logger(f"[7/7] 第 {round_no} 轮检索完成: query={query}, items={len(items)}")

            aggregated_items.extend(round_items)
            deduplicated_items = self._deduplicate_search_items(aggregated_items)
            final_markdown = self.analyzer.enhance_with_network(
                snapshot,
                rolling_summary,
                deduplicated_items,
            )
            final_assessment = self.value_assessor.assess(final_markdown)
            self.logger(
                "[7/7] 第 "
                f"{round_no} 轮增强后价值判断: score={final_assessment.score}, "
                f"valuable={final_assessment.is_valuable}"
            )
            if final_assessment.is_valuable:
                break

        if not final_markdown:
            final_markdown = self.analyzer.render_final_without_network(
                snapshot=snapshot,
                summary=rolling_summary,
                assessment_markdown=assessment_table,
            )
            final_assessment = self.value_assessor.assess(final_markdown)

        detailed_report = FinalReport(
            markdown=final_markdown,
            is_web_enhanced=bool(aggregated_items),
            value_assessment=final_assessment,
        )
        brief_report = self._build_brief_report(snapshot, detailed_report, self._deduplicate_search_items(aggregated_items))
        return ReportBundle(detailed_report=detailed_report, brief_report=brief_report)

    @staticmethod
    def write_report(markdown: str, output_dir: str | Path, filename: str) -> Path:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        path.write_text(markdown, encoding="utf-8")
        return path

    @staticmethod
    def _deduplicate_search_items(items: list[NetworkSearchItem]) -> list[NetworkSearchItem]:
        deduplicated: list[NetworkSearchItem] = []
        seen = set()
        for item in items:
            key = (item.source, item.content[:200])
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(item)
        return deduplicated

    def _build_brief_report(
        self,
        snapshot,
        detailed_report: FinalReport,
        search_items: list[NetworkSearchItem],
    ) -> FinalReport:
        self.logger("[8/9] 生成简报")
        review_feedback = ""
        brief_markdown = ""
        brief_assessment = None
        for round_no in range(1, 3):
            brief_markdown = self.analyzer.render_brief_report(
                snapshot=snapshot,
                detailed_report=detailed_report.markdown,
                search_items=search_items,
                review_feedback=review_feedback,
            )
            brief_assessment = self.brief_value_assessor.assess(brief_markdown)
            self.logger(
                f"[9/9] 简报审核第 {round_no} 轮: score={brief_assessment.score}, "
                f"valuable={brief_assessment.is_valuable}"
            )
            if brief_assessment.is_valuable:
                break
            review_feedback = "请修正以下问题后重新输出简报：" + "；".join(brief_assessment.missing_dimensions)

        return FinalReport(
            markdown=brief_markdown,
            is_web_enhanced=detailed_report.is_web_enhanced,
            value_assessment=brief_assessment or self.brief_value_assessor.assess(brief_markdown),
        )
