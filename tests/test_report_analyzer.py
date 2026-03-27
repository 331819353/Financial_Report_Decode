from financial_report_decode.clients.mock_llm_client import MockLlmClient
from financial_report_decode.models import LocalMetricSnapshot, NetworkSearchItem
from financial_report_decode.services.report_analyzer import ReportAnalyzer


class PlainSnapshot:
    def __init__(self) -> None:
        self.industry = "视听"
        self.year = "2025"
        self.quarter = "H1"
        self.company_name = "TCL电子"
        self.report_title = "TCL电子_2025H1_财务报告.pdf"
        self.metrics = {"公司名": "TCL电子", "营业收入(亿)": "547.77", "非国际报告准则利润": "12.34"}


def test_build_network_queries_uses_missing_dimensions() -> None:
    snapshot = LocalMetricSnapshot(
        industry="视听",
        year="2025",
        quarter="H1",
        company_name="TCL电子",
        report_title="TCL电子_2025H1_财务报告.pdf",
        metrics={"公司名": "TCL电子"},
    )
    analyzer = ReportAnalyzer(MockLlmClient())

    queries = analyzer.build_network_queries(
        snapshot=snapshot,
        current_summary="summary",
        missing_dimensions=["9. 投资者关注点", "7. 展望与指引"],
        asked_queries=[],
    )

    assert len(queries) >= 2
    assert any("分析师" in query or "目标价" in query for query in queries)
    assert any("管理层展望" in query or "行业趋势" in query for query in queries)


def test_render_brief_report_returns_bold_title_paragraphs() -> None:
    snapshot = LocalMetricSnapshot(
        industry="视听",
        year="2025",
        quarter="H1",
        company_name="TCL电子",
        report_title="TCL电子_2025H1_财务报告.pdf",
        metrics={"公司名": "TCL电子", "营业收入(亿)": "547.77"},
    )
    analyzer = ReportAnalyzer(MockLlmClient())

    brief = analyzer.render_brief_report(
        snapshot=snapshot,
        detailed_report="详细报告正文",
        search_items=[NetworkSearchItem(source="https://example.com", content="补充信息")],
    )

    lines = [line for line in brief.splitlines() if line.strip()]
    assert len(lines) >= 5
    assert all(line.startswith("**") and "**：" in line for line in lines)


def test_render_brief_report_supports_snapshot_without_helper_methods() -> None:
    analyzer = ReportAnalyzer(MockLlmClient())

    brief = analyzer.render_brief_report(
        snapshot=PlainSnapshot(),
        detailed_report="详细报告正文",
        search_items=[],
    )

    assert "**TCL电子收入利润双增，经营修复继续兑现**" in brief
