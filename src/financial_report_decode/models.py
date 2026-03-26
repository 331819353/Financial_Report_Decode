from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class AnalysisRequest:
    stock_code: str
    report_date: str
    keyword: str = "营业收入"
    pdf_url: str | None = None
    pdf_path: str | None = None


@dataclass
class LocalMetricSnapshot:
    industry: str
    year: str
    quarter: str
    company_name: str
    report_title: str
    metrics: dict[str, Any]

    def adjusted_profit_metric(self) -> tuple[str, Any] | None:
        metric_priority = [
            "非国际报告准则利润",
            "非国际财务报告准则利润",
            "经调整利润",
            "经调整净利润",
            "non-ifrs profit",
            "adjusted profit",
            "扣非归母净利润(亿)",
            "扣非归母净利润",
            "扣除非经常性损益后的归母净利润",
        ]

        lower_key_map = {key.lower(): key for key in self.metrics}
        for candidate in metric_priority:
            original_key = lower_key_map.get(candidate.lower())
            if original_key is not None:
                return original_key, self.metrics[original_key]
        return None

    def adjusted_profit_display(self) -> str:
        matched = self.adjusted_profit_metric()
        if matched is None:
            return "未披露"
        label, value = matched
        return f"{value}（口径：{label}）"

    def statutory_profit_metric(self) -> tuple[str, Any] | None:
        metric_priority = [
            "归母净利润(亿)",
            "归母净利润",
            "净利润(亿)",
            "净利润",
        ]

        for candidate in metric_priority:
            if candidate in self.metrics:
                return candidate, self.metrics[candidate]
        return None

    def statutory_profit_display(self) -> str:
        matched = self.statutory_profit_metric()
        if matched is None:
            return "未披露"
        label, value = matched
        return f"{value}（口径：{label}）"

    def adjusted_profit_gap_display(self) -> str:
        adjusted = self.adjusted_profit_metric()
        statutory = self.statutory_profit_metric()
        if adjusted is None or statutory is None:
            return "未披露"

        adjusted_value = self._to_decimal(adjusted[1])
        statutory_value = self._to_decimal(statutory[1])
        if adjusted_value is None or statutory_value is None:
            return "未披露"

        gap = adjusted_value - statutory_value
        if gap == 0:
            direction = "与法定利润基本一致"
        elif gap > 0:
            direction = "高于法定利润"
        else:
            direction = "低于法定利润"
        return f"{gap:.2f}（{direction}）"

    def adjusted_profit_gap_reason_display(self) -> str:
        gap_display = self.adjusted_profit_gap_display()
        if gap_display == "未披露":
            return "未披露"
        return "需结合财报或补充信息判断是否由非经常性损益、投资收益、公允价值变动、汇兑损益或减值项目导致"

    def normalized_metrics(self) -> dict[str, Any]:
        normalized = dict(self.metrics)
        normalized.setdefault("调整后利润", self.adjusted_profit_display())
        normalized.setdefault("法定利润", self.statutory_profit_display())
        normalized.setdefault("调整后利润与法定利润差异", self.adjusted_profit_gap_display())
        normalized.setdefault("调整后利润差异原因", self.adjusted_profit_gap_reason_display())
        return normalized

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        try:
            return Decimal(str(value).replace(",", "").strip())
        except (InvalidOperation, AttributeError):
            return None


@dataclass
class NetworkSearchItem:
    source: str
    content: str


@dataclass
class PdfChunk:
    chunk_id: int
    text: str
    start: int
    end: int


@dataclass
class AnalysisStageResult:
    summary: str
    insights: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class ValueAssessment:
    is_valuable: bool
    score: int
    reasoning: str
    missing_dimensions: list[str] = field(default_factory=list)


@dataclass
class FinalReport:
    markdown: str
    is_web_enhanced: bool
    value_assessment: ValueAssessment


@dataclass
class ReportBundle:
    detailed_report: FinalReport
    brief_report: FinalReport


@dataclass(frozen=True)
class PersistedFinancialReport:
    company_code: str
    industry: str
    summary: str
    company_name: str
    report_type: str
    quarter: str
    year: str
    report_title: str
