from financial_report_decode.main import build_persisted_report, build_report_title
from financial_report_decode.clients.report_db_client import ReportDbClient
from financial_report_decode.models import (
    AnalysisRequest,
    FinalReport,
    LocalMetricSnapshot,
    PersistedFinancialReport,
    ValueAssessment,
)


class FakeCursor:
    def __init__(self) -> None:
        self.executed = []
        self.closed = False

    def execute(self, sql: str, params: tuple) -> None:
        self.executed.append((sql, params))

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


class FakeDriver:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.connect_kwargs = None

    def connect(self, **kwargs) -> FakeConnection:
        self.connect_kwargs = kwargs
        return self.connection


def test_upsert_report_executes_expected_sql() -> None:
    driver = FakeDriver()
    client = ReportDbClient(
        host="127.0.0.1",
        port=3306,
        user="tester",
        password="secret",
        database="reports",
        table="caibao_financial_reports",
        driver=driver,
    )
    report = PersistedFinancialReport(
        company_code="1070.HK",
        industry="视听",
        summary="最终报告正文",
        company_name="TCL电子",
        report_type="半年报",
        quarter="H1",
        year="2025",
        report_title="TCL电子_2025H1_财务报告.pdf",
    )

    client.upsert_report(report)

    assert driver.connect_kwargs == {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "tester",
        "password": "secret",
        "database": "reports",
        "connect_timeout": 30,
        "charset": "utf8mb4",
    }
    sql, params = driver.connection.cursor_instance.executed[0]
    assert "INSERT INTO caibao_financial_reports" in sql
    assert "conclusion" in sql
    assert params == (
        "1070.HK",
        "视听",
        "TCL电子_2025H1_财务报告.pdf",
        "2025",
        "H1",
        "半年报",
        "TCL电子",
        "最终报告正文",
        None,
    )
    assert driver.connection.committed is True
    assert driver.connection.cursor_instance.closed is True
    assert driver.connection.closed is True


def test_upsert_report_writes_dr_content_to_conclusion() -> None:
    driver = FakeDriver()
    client = ReportDbClient(
        host="127.0.0.1",
        port=3306,
        user="tester",
        password="secret",
        database="reports",
        table="caibao_financial_reports",
        driver=driver,
    )
    report = PersistedFinancialReport(
        company_code="1070.HK",
        industry="视听",
        summary="详报正文",
        company_name="TCL电子",
        report_type="DR",
        quarter="H1",
        year="2025",
        report_title="TCL电子_2025H1_财务报告_DR.pdf",
    )

    client.upsert_report(report)

    _, params = driver.connection.cursor_instance.executed[0]
    assert params == (
        "1070.HK",
        "视听",
        "TCL电子_2025H1_财务报告_DR.pdf",
        "2025",
        "H1",
        "DR",
        "TCL电子",
        None,
        "详报正文",
    )


def test_upsert_report_writes_br_content_to_summary() -> None:
    driver = FakeDriver()
    client = ReportDbClient(
        host="127.0.0.1",
        port=3306,
        user="tester",
        password="secret",
        database="reports",
        table="caibao_financial_reports",
        driver=driver,
    )
    report = PersistedFinancialReport(
        company_code="1070.HK",
        industry="视听",
        summary="简报正文",
        company_name="TCL电子",
        report_type="BR",
        quarter="H1",
        year="2025",
        report_title="TCL电子_2025H1_财务报告_BR.pdf",
    )

    client.upsert_report(report)

    _, params = driver.connection.cursor_instance.executed[0]
    assert params == (
        "1070.HK",
        "视听",
        "TCL电子_2025H1_财务报告_BR.pdf",
        "2025",
        "H1",
        "BR",
        "TCL电子",
        "简报正文",
        None,
    )
    assert driver.connection.committed is True


def test_upsert_report_requires_complete_config() -> None:
    client = ReportDbClient(
        host="",
        port=3306,
        user="tester",
        password="secret",
        database="reports",
        table="caibao_financial_reports",
        driver=FakeDriver(),
    )
    report = PersistedFinancialReport(
        company_code="1070.HK",
        industry="视听",
        summary="最终报告正文",
        company_name="TCL电子",
        report_type="半年报",
        quarter="H1",
        year="2025",
        report_title="TCL电子_2025H1_财务报告.pdf",
    )

    try:
        client.upsert_report(report)
    except ValueError as exc:
        assert "host" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_build_persisted_report_defaults_report_type_to_dr() -> None:
    request = AnalysisRequest(stock_code="1070.HK", report_date="2025-06-30")
    snapshot = LocalMetricSnapshot(
        industry="视听",
        year="2025",
        quarter="H1",
        company_name="TCL电子",
        report_title="TCL电子_2025H1_财务报告.pdf",
        metrics={},
    )
    final_report = FinalReport(
        markdown="最终报告正文",
        is_web_enhanced=False,
        value_assessment=ValueAssessment(is_valuable=True, score=90, reasoning="ok"),
    )

    report = build_persisted_report(request, snapshot, final_report)

    assert report.report_type == "DR"


def test_build_report_title_appends_report_type_suffix() -> None:
    snapshot = LocalMetricSnapshot(
        industry="视听",
        year="2025",
        quarter="H1",
        company_name="TCL电子",
        report_title="TCL电子_2025H1_财务报告.pdf",
        metrics={},
    )

    assert build_report_title(snapshot, "BR") == "TCL电子_2025H1_财务报告_BR.pdf"
