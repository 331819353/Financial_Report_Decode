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
