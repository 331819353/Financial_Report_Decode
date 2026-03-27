from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
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

    @property
    def adjusted_profit_metric(self) -> tuple[str, Any] | None:
        return snapshot_adjusted_profit_metric(self)

    @property
    def adjusted_profit_display(self) -> str:
        return snapshot_adjusted_profit_display(self)

    @property
    def statutory_profit_metric(self) -> tuple[str, Any] | None:
        return snapshot_statutory_profit_metric(self)

    @property
    def statutory_profit_display(self) -> str:
        return snapshot_statutory_profit_display(self)

    @property
    def adjusted_profit_gap_display(self) -> str:
        return snapshot_adjusted_profit_gap_display(self)

    @property
    def adjusted_profit_gap_reason_display(self) -> str:
        return snapshot_adjusted_profit_gap_reason_display(self)

    @property
    def normalized_metrics(self) -> dict[str, Any]:
        return snapshot_normalized_metrics(self)

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


def snapshot_metrics(snapshot: Any) -> dict[str, Any]:
    metrics = getattr(snapshot, "metrics", None)
    if isinstance(metrics, dict):
        return metrics
    if isinstance(snapshot, dict):
        return snapshot
    return {}


def snapshot_metric_value(snapshot: Any, aliases: list[str], fuzzy: bool = True) -> Any | None:
    matched = snapshot_metric_entry(snapshot, aliases, fuzzy)
    if matched is None:
        return None
    return matched[1]


def snapshot_metric_entry(snapshot: Any, aliases: list[str], fuzzy: bool = True) -> tuple[str, Any] | None:
    metrics = snapshot_metrics(snapshot)
    if not metrics:
        return None

    normalized_key_map = {_normalize_metric_key(key): key for key in metrics}
    for alias in aliases:
        normalized_alias = _normalize_metric_key(alias)
        original_key = normalized_key_map.get(normalized_alias)
        if original_key is not None:
            return original_key, metrics[original_key]

    if not fuzzy:
        return None

    for alias in aliases:
        normalized_alias = _normalize_metric_key(alias)
        for key, value in metrics.items():
            normalized_key = _normalize_metric_key(key)
            if normalized_alias in normalized_key or normalized_key in normalized_alias:
                return key, value
    return None


def snapshot_company_name(snapshot: Any) -> str:
    company_name = getattr(snapshot, "company_name", "")
    if company_name:
        return str(company_name)
    value = snapshot_metric_value(snapshot, ["公司名"], fuzzy=False)
    return str(value) if value not in (None, "") else ""


def snapshot_industry(snapshot: Any) -> str:
    industry = getattr(snapshot, "industry", "")
    if industry:
        return str(industry)
    value = snapshot_metric_value(snapshot, ["子行业"], fuzzy=False)
    return str(value) if value not in (None, "") else ""


def snapshot_adjusted_profit_metric(snapshot: Any) -> tuple[str, Any] | None:
    return snapshot_metric_entry(
        snapshot,
        [
            "非国际报告准则利润",
            "非国际财务报告准则利润",
            "经调整利润",
            "经调整净利润",
            "non-ifrs profit",
            "adjusted profit",
            "扣非归母净利润(亿)",
            "扣非归母净利润",
            "扣除非经常性损益后的归母净利润",
        ],
    )


def snapshot_adjusted_profit_display(snapshot: Any) -> str:
    matched = snapshot_adjusted_profit_metric(snapshot)
    if matched is None:
        return "未披露"
    label, value = matched
    return f"{value}（口径：{label}）"


def snapshot_statutory_profit_metric(snapshot: Any) -> tuple[str, Any] | None:
    return snapshot_metric_entry(
        snapshot,
        [
            "归母净利润(亿)",
            "归母净利润",
            "净利润(亿)",
            "净利润",
        ],
    )


def snapshot_statutory_profit_display(snapshot: Any) -> str:
    matched = snapshot_statutory_profit_metric(snapshot)
    if matched is None:
        return "未披露"
    label, value = matched
    return f"{value}（口径：{label}）"


def snapshot_adjusted_profit_gap_display(snapshot: Any) -> str:
    adjusted = snapshot_adjusted_profit_metric(snapshot)
    statutory = snapshot_statutory_profit_metric(snapshot)
    if adjusted is None or statutory is None:
        return "未披露"

    adjusted_value = LocalMetricSnapshot._to_decimal(adjusted[1])
    statutory_value = LocalMetricSnapshot._to_decimal(statutory[1])
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


def snapshot_adjusted_profit_gap_reason_display(snapshot: Any) -> str:
    gap_display = snapshot_adjusted_profit_gap_display(snapshot)
    if gap_display == "未披露":
        return "未披露"
    return "需结合财报或补充信息判断是否由非经常性损益、投资收益、公允价值变动、汇兑损益或减值项目导致"


def snapshot_normalized_metrics(snapshot: Any) -> dict[str, Any]:
    normalized = dict(snapshot_metrics(snapshot))

    # 仅当能明确提取出指标时才填充规范化字段，否则交由 LLM 从原始数据中识别
    adj_profit = snapshot_adjusted_profit_display(snapshot)
    if adj_profit != "未披露":
        normalized.setdefault("调整后利润", adj_profit)

    stat_profit = snapshot_statutory_profit_display(snapshot)
    if stat_profit != "未披露":
        normalized.setdefault("法定利润", stat_profit)

    gap = snapshot_adjusted_profit_gap_display(snapshot)
    if gap != "未披露":
        normalized.setdefault("调整后利润与法定利润差异", gap)
        normalized.setdefault("调整后利润差异原因", snapshot_adjusted_profit_gap_reason_display(snapshot))

    return normalized


def _normalize_metric_key(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "", str(value)).lower()
