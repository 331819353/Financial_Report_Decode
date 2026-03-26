from financial_report_decode.clients.local_db_client import LocalDbClient


def test_build_snapshot_from_payload() -> None:
    payload = {
        "company_name": "TCL电子",
        "industry": "视听",
        "quarter": "H1",
        "report_title": "TCL电子_2025H1_财务报告.pdf",
        "result": "{\"公司名\": \"TCL电子\", \"子行业\": \"视听\", \"营业收入(亿)\": \"547.77\"}",
        "year": "2025",
    }
    snapshot = LocalDbClient().build_snapshot_from_payload(payload, "2025-06-30")

    assert snapshot.company_name == "TCL电子"
    assert snapshot.industry == "视听"
    assert snapshot.quarter == "H1"
    assert snapshot.metrics["营业收入(亿)"] == "547.77"


def test_adjusted_profit_mapping_for_hk() -> None:
    payload = {
        "company_name": "TCL电子",
        "industry": "视听",
        "quarter": "H1",
        "report_title": "TCL电子_2025H1_财务报告.pdf",
        "result": "{\"公司名\": \"TCL电子\", \"非国际报告准则利润\": \"12.34\", \"净利润(亿)\": \"11.09\"}",
        "year": "2025",
    }
    snapshot = LocalDbClient().build_snapshot_from_payload(payload, "2025-06-30")

    assert snapshot.adjusted_profit_metric() == ("非国际报告准则利润", "12.34")
    assert snapshot.adjusted_profit_display() == "12.34（口径：非国际报告准则利润）"
    assert snapshot.statutory_profit_display() == "11.09（口径：净利润(亿)）"
    assert snapshot.adjusted_profit_gap_display() == "1.25（高于法定利润）"


def test_adjusted_profit_mapping_for_a_share() -> None:
    payload = {
        "company_name": "示例公司",
        "industry": "家电",
        "quarter": "H1",
        "report_title": "示例公司_2025H1_财务报告.pdf",
        "result": "{\"公司名\": \"示例公司\", \"扣非归母净利润(亿)\": \"8.88\"}",
        "year": "2025",
    }
    snapshot = LocalDbClient().build_snapshot_from_payload(payload, "2025-06-30")

    assert snapshot.adjusted_profit_metric() == ("扣非归母净利润(亿)", "8.88")
    assert snapshot.adjusted_profit_display() == "8.88（口径：扣非归母净利润(亿)）"


def test_adjusted_profit_gap_display() -> None:
    payload = {
        "company_name": "示例公司",
        "industry": "家电",
        "quarter": "H1",
        "report_title": "示例公司_2025H1_财务报告.pdf",
        "result": "{\"公司名\": \"示例公司\", \"扣非归母净利润(亿)\": \"8.88\", \"净利润(亿)\": \"8.10\"}",
        "year": "2025",
    }
    snapshot = LocalDbClient().build_snapshot_from_payload(payload, "2025-06-30")

    assert snapshot.statutory_profit_metric() == ("净利润(亿)", "8.10")
    assert snapshot.adjusted_profit_gap_display() == "0.78（高于法定利润）"
