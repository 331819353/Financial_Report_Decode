from financial_report_decode.models import LocalMetricSnapshot
from financial_report_decode.utils.markdown import metrics_table


def test_metrics_table_includes_normalized_adjusted_profit() -> None:
    snapshot = LocalMetricSnapshot(
        industry="视听",
        year="2025",
        quarter="H1",
        company_name="TCL电子",
        report_title="TCL电子_2025H1_财务报告.pdf",
        metrics={"非国际报告准则利润": "12.34", "净利润": "10.00"},
    )

    table = metrics_table(snapshot)

    assert "调整后利润" in table
    assert "12.34（口径：非国际报告准则利润）" in table
    assert "调整后利润差异原因" in table
