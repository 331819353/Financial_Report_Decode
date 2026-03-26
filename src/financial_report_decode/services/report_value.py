from __future__ import annotations

import re

from financial_report_decode.models import ValueAssessment


class ReportValueAssessor:
    REQUIRED_SECTIONS = [
        "## 1. 财报概况",
        "## 2. 收入与盈利分析",
        "## 3. 成本与费用分析",
        "## 4. 现金流情况",
        "## 5. 财务状况",
        "## 6. 运营表现",
        "## 7. 展望与指引",
        "## 8. 风险因素",
        "## 9. 投资者关注点",
    ]

    def assess(self, markdown: str) -> ValueAssessment:
        score = 0
        missing = []

        for section in self.REQUIRED_SECTIONS:
            if section in markdown:
                score += 8
            else:
                missing.append(section.replace("## ", ""))

        if "| 指标 | 结果 |" in markdown or "| 项目 | 结果 |" in markdown:
            score += 10
        else:
            missing.append("至少 1 个结构化表格")

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

        disclosed_hits = markdown.count("未披露")
        if disclosed_hits >= 3:
            score += 8
        else:
            missing.append("对未披露项的显式处理")

        is_valuable = score >= 75
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


class BriefReportAssessor:
    def assess(self, markdown: str) -> ValueAssessment:
        score = 0
        missing = []

        lines = [line.strip() for line in markdown.splitlines() if line.strip()]
        if len(lines) >= 4:
            score += 30
        else:
            missing.append("至少 4 段简报结论")

        bold_title_lines = [line for line in lines if re.match(r"^\*\*.+\*\*：.+", line)]
        if len(bold_title_lines) == len(lines) and lines:
            score += 30
        else:
            missing.append("每段以加粗标题开头")

        digit_hits = len(re.findall(r"\d", markdown))
        if digit_hits >= 6:
            score += 20
        else:
            missing.append("必要的量化指标")

        if all(keyword not in markdown for keyword in ("数据库", "网络检索", "知识库", "数据来源")):
            score += 20
        else:
            missing.append("不要出现来源说明")

        is_valuable = score >= 80
        reasoning = (
            "简报结构完整，提炼重点明确，可直接写入数据库。"
            if is_valuable
            else "简报结构或量化信息不足，需要继续修订。"
        )
        return ValueAssessment(
            is_valuable=is_valuable,
            score=score,
            reasoning=reasoning,
            missing_dimensions=missing,
        )
