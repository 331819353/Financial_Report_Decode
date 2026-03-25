from __future__ import annotations

import json

from financial_report_decode.clients.llm_client import LlmClient
from financial_report_decode.models import (
    AnalysisStageResult,
    LocalMetricSnapshot,
    NetworkSearchItem,
    PdfChunk,
)
from financial_report_decode.utils.markdown import metrics_table, network_table, value_table


class ReportAnalyzer:
    def __init__(self, llm_client: LlmClient) -> None:
        self.llm_client = llm_client

    def analyze_baseline(self, snapshot: LocalMetricSnapshot) -> AnalysisStageResult:
        prompt = f"""
你是一名资深财报分析师。请根据以下公司基础指标，生成初步财报分析。

要求：
1. 输出公司概况、经营表现、盈利能力、现金流或资产负债、风险与展望。
2. 提炼 3-5 条洞察和 2-3 条风险点。
3. 仅基于给定数据，不要编造未提供的事实。

公司信息：
公司名：{snapshot.company_name}
行业：{snapshot.industry}
报告期：{snapshot.year} {snapshot.quarter}

指标数据：
{json.dumps(snapshot.metrics, ensure_ascii=False, indent=2)}
"""
        result = self.llm_client.complete(
            system_prompt="你负责输出专业、审慎、结构清晰的中文财报分析。",
            user_prompt=prompt,
        )
        return AnalysisStageResult(summary=result)

    def analyze_chunks(
        self,
        snapshot: LocalMetricSnapshot,
        chunks: list[PdfChunk],
        baseline_summary: str,
    ) -> str:
        rolling_summary = baseline_summary
        total = len(chunks)

        for chunk in chunks:
            prompt = f"""
你正在递进式解读上市公司财报，请结合上一轮总结和当前文本块，更新总分析。

要求：
1. 保留已确认的重要结论，删除明显重复。
2. 强化经营表现、盈利质量、现金流、资产负债、风险事项、管理层表述。
3. 如果当前块包含数字、表格描述、重大事项，应优先纳入。
4. 输出应为下一轮可继续承接的总结，不少于 500 字。

公司：{snapshot.company_name}
行业：{snapshot.industry}
报告期：{snapshot.year} {snapshot.quarter}
当前块：{chunk.chunk_id}/{total}

上一轮总结：
{rolling_summary}

当前文本块：
{chunk.text}
"""
            rolling_summary = self.llm_client.complete(
                system_prompt="你负责持续迭代更新财报综合解读，不遗漏关键信息。",
                user_prompt=prompt,
            )

        return rolling_summary

    def enhance_with_network(
        self,
        snapshot: LocalMetricSnapshot,
        current_summary: str,
        search_items: list[NetworkSearchItem],
    ) -> str:
        prompt = f"""
请结合现有财报总结和外部网络检索结果，生成一份最终财报专业解读。

要求：
1. 必须输出 Markdown。
2. 必须包含标题、执行摘要、关键指标表、详细分析、风险与展望、洞察结论、信息来源。
3. 详细分析中要覆盖公司概况、经营表现、盈利能力、现金流或资产负债、风险与展望。
4. 结尾给出至少 3 条有分析价值的洞察结论。

公司信息：
公司名：{snapshot.company_name}
行业：{snapshot.industry}
报告期：{snapshot.year} {snapshot.quarter}

本地指标表：
{metrics_table(snapshot)}

现有财报总结：
{current_summary}

网络检索结果：
{network_table(search_items)}
"""
        return self.llm_client.complete(
            system_prompt="你输出面向专业读者的中文 Markdown 财报解读报告。",
            user_prompt=prompt,
        )

    def render_final_without_network(
        self,
        snapshot: LocalMetricSnapshot,
        summary: str,
        assessment_markdown: str,
    ) -> str:
        prompt = f"""
请把下面内容整理为最终 Markdown 财报解读报告。

要求：
1. 包含标题、执行摘要、关键指标表、详细分析、风险与展望、洞察结论、价值判断。
2. 使用 Markdown 表格展示关键指标和价值判断。
3. 详细分析需覆盖公司概况、经营表现、盈利能力、现金流或资产负债、风险与展望。

公司信息：
公司名：{snapshot.company_name}
行业：{snapshot.industry}
报告期：{snapshot.year} {snapshot.quarter}

关键指标表：
{metrics_table(snapshot)}

综合分析：
{summary}

价值判断：
{assessment_markdown}
"""
        return self.llm_client.complete(
            system_prompt="你输出结构化、专业、中文 Markdown 报告。",
            user_prompt=prompt,
        )

    @staticmethod
    def render_assessment_table(markdown_assessment) -> str:
        return value_table(markdown_assessment)

