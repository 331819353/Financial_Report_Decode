from __future__ import annotations

from financial_report_decode.models import LocalMetricSnapshot, NetworkSearchItem, ValueAssessment


def metrics_table(snapshot: LocalMetricSnapshot) -> str:
    rows = ["| 指标 | 数值 |", "| --- | --- |"]
    for key, value in snapshot.metrics.items():
        rows.append(f"| {key} | {value} |")
    return "\n".join(rows)


def network_table(items: list[NetworkSearchItem]) -> str:
    if not items:
        return "无网络补充信息。"

    rows = ["| 来源 | 主要内容 |", "| --- | --- |"]
    for item in items:
        content = item.content.replace("\n", " ").strip()
        rows.append(f"| {item.source} | {content} |")
    return "\n".join(rows)


def value_table(assessment: ValueAssessment) -> str:
    missing = "；".join(assessment.missing_dimensions) if assessment.missing_dimensions else "无"
    rows = [
        "| 维度 | 结果 |",
        "| --- | --- |",
        f"| 是否达标 | {'是' if assessment.is_valuable else '否'} |",
        f"| 评分 | {assessment.score} |",
        f"| 判断说明 | {assessment.reasoning} |",
        f"| 缺失项 | {missing} |",
    ]
    return "\n".join(rows)

