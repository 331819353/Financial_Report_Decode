from financial_report_decode.clients.mock_llm_client import MockLlmClient
from financial_report_decode.models import LocalMetricSnapshot
from financial_report_decode.services.report_analyzer import ReportAnalyzer


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
