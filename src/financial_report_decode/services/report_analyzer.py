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
        prompt = self._baseline_prompt(snapshot)
        result = self.llm_client.complete(
            system_prompt=self._system_prompt(),
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
            prompt = self._chunk_prompt(snapshot, chunk, total, rolling_summary)
            rolling_summary = self.llm_client.complete(
                system_prompt=self._system_prompt(),
                user_prompt=prompt,
            )

        return rolling_summary

    def enhance_with_network(
        self,
        snapshot: LocalMetricSnapshot,
        current_summary: str,
        search_items: list[NetworkSearchItem],
    ) -> str:
        prompt = self._final_prompt(
            snapshot=snapshot,
            current_summary=current_summary,
            assessment_markdown="",
            network_markdown=network_table(search_items),
            include_network=True,
        )
        return self.llm_client.complete(
            system_prompt=self._system_prompt(),
            user_prompt=prompt,
        )

    def build_network_queries(
        self,
        snapshot: LocalMetricSnapshot,
        current_summary: str,
        missing_dimensions: list[str],
        asked_queries: list[str],
    ) -> list[str]:
        report_period = f"{snapshot.year}年{snapshot.quarter}"
        dimension_map = {
            "6. 运营表现": [
                f"{snapshot.company_name}{report_period}市场份额变化",
                f"{snapshot.company_name}{report_period}地区收入增长 中东非 欧洲 拉美",
                f"{snapshot.company_name}{report_period}新品 高端显示 业务进展",
            ],
            "7. 展望与指引": [
                f"{snapshot.company_name}{report_period}管理层展望 指引 战略规划",
                f"{snapshot.company_name}{report_period}行业趋势 电视 显示 增长",
            ],
            "8. 风险因素": [
                f"{snapshot.company_name}{report_period}风险 汇率 库存 海外需求",
                f"{snapshot.company_name}{report_period}价格竞争 原材料 风险",
            ],
            "9. 投资者关注点": [
                f"{snapshot.company_name}{report_period}分析师 评级 目标价",
                f"{snapshot.company_name}{report_period}业绩后 股价 表现 市场预期",
            ],
            "至少 3 条洞察结论": [
                f"{snapshot.company_name}{report_period}核心看点 经营亮点",
            ],
        }

        fallback_queries = [
            f"{snapshot.company_name}{report_period}业务分部 收入增长",
            f"{snapshot.company_name}{report_period}海外市场 表现",
            f"{snapshot.company_name}{report_period}投资者关注点",
        ]

        queries: list[str] = []
        for missing in missing_dimensions:
            for query in dimension_map.get(missing, []):
                if query not in asked_queries and query not in queries:
                    queries.append(query)

        for query in fallback_queries:
            if len(queries) >= 3:
                break
            if query not in asked_queries and query not in queries:
                queries.append(query)

        return queries[:3]

    def render_final_without_network(
        self,
        snapshot: LocalMetricSnapshot,
        summary: str,
        assessment_markdown: str,
    ) -> str:
        prompt = self._final_prompt(
            snapshot=snapshot,
            current_summary=summary,
            assessment_markdown=assessment_markdown,
            network_markdown="无网络补充信息。",
            include_network=False,
        )
        return self.llm_client.complete(
            system_prompt=self._system_prompt(),
            user_prompt=prompt,
        )

    @staticmethod
    def render_assessment_table(markdown_assessment) -> str:
        return value_table(markdown_assessment)

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是一位具有多年市场行情分析经验的财报解读专家。"
            "你必须严格依据提供材料输出中文 Markdown 报告。"
            "不得编造未披露数据；若财报和现有材料都未给出，必须明确写“未披露”。"
            "不要输出思考过程、限制性说明、来源说明。"
            "营业收入与营业总收入必须区分，不能混淆。"
        )

    def _baseline_prompt(self, snapshot: LocalMetricSnapshot) -> str:
        prompt = f"""
任务：先基于已有基础指标，生成“财报解读中间结论”，供后续财报原文逐块补强。

要求：
1. 明确当前已能确认的指标、仍缺失的指标、需要重点去财报原文佐证的内容。
2. 重点围绕财务健康状况、业务表现、未来前景、风险四个方向组织。
3. 对未提供的数据显式写“未披露”，不要猜测。
4. 输出为后续可累积更新的中间总结，不要直接输出最终报告。
5. 优先覆盖这些指标：
   - 偿债能力：流动比率、速动比率、资产负债率、利息保障倍数
   - 盈利能力：毛利率、净利率、净资产收益率、资产回报率
   - 运营效率：存货周转率、应收账款周转率、总资产周转率
   - 业务表现：营业收入、营业总收入、净利润、营业利润率、市场份额、客户与员工指标
   - 前景：收入增长率、营运利润增长率、研发投入、行业趋势、战略规划、风险

公司信息：
公司名：{snapshot.company_name}
行业：{snapshot.industry}
报告期：{snapshot.year} {snapshot.quarter}

指标数据：
{json.dumps(snapshot.metrics, ensure_ascii=False, indent=2)}
"""
        return prompt

    def _chunk_prompt(
        self,
        snapshot: LocalMetricSnapshot,
        chunk: PdfChunk,
        total_chunks: int,
        rolling_summary: str,
    ) -> str:
        prompt = f"""
任务：结合上一轮中间结论与当前财报文本块，继续补全和修正财报解读。

要求：
1. 保留已确认结论，修正与当前文本不一致的地方，补充新发现。
2. 尤其关注这些内容是否在当前块中出现：收入分业务/分区域、利润变化原因、费用结构、现金流、资产负债、研发投入、战略方向、风险提示。
3. 对每项指标给出“已确认/未披露/待后续块确认”状态，不要编造。
4. 如果文本中出现多组数据，优先保留与当前报告期累计口径一致的数据。
5. 输出仍为“中间结论”，供下一块继续承接，不直接生成最终报告。

公司信息：
公司名：{snapshot.company_name}
行业：{snapshot.industry}
报告期：{snapshot.year} {snapshot.quarter}
当前块：{chunk.chunk_id}/{total_chunks}

上一轮中间结论：
{rolling_summary}

当前文本块：
{chunk.text}
"""
        return prompt

    def _final_prompt(
        self,
        snapshot: LocalMetricSnapshot,
        current_summary: str,
        assessment_markdown: str,
        network_markdown: str,
        include_network: bool,
    ) -> str:
        network_requirement = (
            "可结合补充信息完善市场预期、行业趋势、投资者关注点等内容，但仍不得编造。"
            if include_network
            else "若相关信息未在材料中出现，必须明确写“未披露”。"
        )
        return f"""
任务：根据中间结论和现有材料，输出最终财报解读报告。

必须遵守：
1. 严格按下述模板输出，使用 Markdown。
2. 每个分析角度都必须先给简洁总结，再给表格说明。
3. 未披露的数据或结论直接写“未披露”。
4. 不要输出数据来源，不要输出思考过程，不要输出限制性说明。
5. 所有时间维度都按累计口径理解，当前报告期为 {snapshot.year}{snapshot.quarter}。
6. {network_requirement}
7. 在“收入与盈利分析、成本与费用分析、现金流情况、财务状况、运营表现、展望与指引”六个部分中，都必须附带一个 Markdown 表格，表头固定为：
   | 分析角度 | 指标/主题 | 本期表现 | 变化情况/影响 | 核心策略关键词 |
8. “变化情况/影响”需要解释指标变化对经营质量、增长动能、盈利能力、现金流安全或竞争格局的影响。
9. “核心策略关键词”要简洁，适合管理层策略提炼，如“全球化扩张、结构升级、费用优化、库存控制、研发加码”等。

输出格式：
1. **财报概况**
   - **报告期**：__
   - **营业总收入**：__
   - **净利润**：__
   - **每股收益（EPS）**：__
   - **毛利率**：__
   - **营业利润率**：__

2. **收入与盈利分析**
   - **主要收入来源**：__
   - **收入增长**：__
   - **收入细分分析**：
     - **核心业务**：__
     - **新业务/新市场**：__
   - **盈利能力分析**：
     - **毛利率**：__
     - **营业利润率**：__
     - **净利润率**：__
   - **业务板块分析**：
     - **产品/服务板块**：__
     - **地域市场**：__
   - **核心战略关键词**：__
   - 提供“收入与盈利分析”表格。
   - 自动总结各业务板块的收入和增长情况，以列表形式输出。

3. **成本与费用分析**
   - **主要成本变化**：__
   - **费用分析**：
     - **研发费用**：__
     - **销售费用**：__
     - **管理费用**：__
     - **其他费用**：__
   - **成本/费用细分**：
     - **直接成本**：__
     - **间接费用**：__
   - **费用占比变化**：__
   - 提供“成本与费用分析”表格。
   - 自动总结成本与费用指标变化及策略关键词，以列表形式输出。

4. **现金流情况**
   - **自由现金流**：__
   - **经营活动现金流**：__
   - **现金及现金等价物**：__
   - **资本支出**：__
   - 提供“现金流情况”表格。

5. **财务状况**
   - **资产负债表概况**：
     - **总资产**：__
     - **负债情况**：__
     - **股东权益**：__
   - **流动比率/速动比率**：__
   - **资本结构分析**：
     - **债务股本比**：__
     - **资本支出增长**：__
   - 提供“财务状况”表格。
   - 自动总结财务状况指标变化及策略关键词，以列表形式输出。

6. **运营表现**
   - **客户增长**：
     - **活跃用户数**：__
     - **用户留存率**：__
     - **市场份额**：__
   - **产品/服务表现**：
     - **新产品推出**：__
     - **现有产品表现**：__
   - **地区市场表现**：__
   - 提供“运营表现”表格。
   - 自动总结营运指标及策略关键词，以列表形式输出。

7. **展望与指引**
   - **未来财季指引**：__
   - **管理层战略方向**：
     - **扩展市场**：__
     - **创新产品投入**：__
   - **长期战略**：__
   - 提供“展望与指引”表格。

8. **风险因素**
   - **外部风险**：__

9. **投资者关注点**
   - 分析师/投资者反应：__
   - 市场预期：__

公司信息：
公司名：{snapshot.company_name}
行业：{snapshot.industry}
报告期：{snapshot.year} {snapshot.quarter}

本地指标表：
{metrics_table(snapshot)}

中间结论：
{current_summary}

价值判断：
{assessment_markdown or "无"}

补充信息：
{network_markdown}
"""
