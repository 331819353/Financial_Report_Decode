from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnalysisRequest:
    stock_code: str
    report_date: str
    keyword: str = "营业收入"
    pdf_url: str | None = None


@dataclass
class LocalMetricSnapshot:
    industry: str
    year: str
    quarter: str
    company_name: str
    report_title: str
    metrics: dict[str, Any]


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

