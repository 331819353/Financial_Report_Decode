from __future__ import annotations

import re

from financial_report_decode.models import ValueAssessment


class ReportValueAssessor:
    REQUIRED_DIMENSIONS = [
        "公司概况",
        "经营表现",
        "盈利能力",
        "现金流或资产负债",
        "风险与展望",
    ]

    def assess(self, markdown: str) -> ValueAssessment:
        score = 0
        missing = []

        for dimension in self.REQUIRED_DIMENSIONS:
            if dimension in markdown:
                score += 20
            else:
                missing.append(dimension)

        insight_hits = len(re.findall(r"(?m)^- ", markdown))
        if insight_hits >= 3:
            score += 10
        else:
            missing.append("至少 3 条洞察结论")

        digit_hits = len(re.findall(r"\d", markdown))
        if digit_hits >= 10:
            score += 10
        else:
            missing.append("量化指标或趋势描述")

        is_valuable = score >= 80
        reasoning = (
            "分析结果已覆盖关键维度，且具备一定量化支撑。"
            if is_valuable
            else "分析结果仍存在关键维度缺失或量化不足，需要网络检索增强。"
        )
        return ValueAssessment(
            is_valuable=is_valuable,
            score=score,
            reasoning=reasoning,
            missing_dimensions=missing,
        )

