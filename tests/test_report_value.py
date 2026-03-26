from financial_report_decode.services.report_value import BriefReportAssessor, ReportValueAssessor


def test_value_assessor_high_value() -> None:
    markdown = """
# 标题
## 1. 财报概况
2025年上半年公司收入123，利润456。
| 指标 | 结果 |
| --- | --- |
| 营业总收入 | 123 |
| 净利润 | 456 |
## 2. 收入与盈利分析
收入增长12%，销量增长8%。
## 3. 成本与费用分析
研发费用10，销售费用20。
## 4. 现金流情况
经营现金流789，资本支出100。
## 5. 财务状况
资产负债率40%，流动比率1.2。
## 6. 运营表现
市场份额未披露，用户留存率未披露。
## 7. 展望与指引
未来财季指引未披露。
## 8. 风险因素
原材料波动、需求承压，但新产品推进。
## 9. 投资者关注点
分析师/投资者反应未披露，市场预期未披露。
- 洞察1
- 洞察2
- 洞察3
"""
    result = ReportValueAssessor().assess(markdown)
    assert result.is_valuable is True
    assert result.score >= 80


def test_brief_value_assessor_high_value() -> None:
    markdown = """
**公司收入利润双增，经营修复继续兑现**：2025年H1公司收入547.77亿、净利润10.48亿，盈利修复趋势明确。
**公司显示主业扩张，海外布局带动新增量**：核心业务维持增长，中东非、欧洲、拉美等区域拓展继续推进。
**公司成本费用仍有压力，盈利质量待优化**：营业成本464.11亿、销售费用40.12亿、研发费用11.54亿，对利润率形成约束。
**公司现金流保持为正，短债与营运资本占用需关注**：经营活动现金流6.93亿，货币资金114.42亿，但高杠杆仍需观察。
**公司推进高端升级，后续聚焦全球化与盈利改善**：产品结构升级和运营提效仍是后续核心主线。
"""
    result = BriefReportAssessor().assess(markdown)
    assert result.is_valuable is True
    assert result.score >= 80
