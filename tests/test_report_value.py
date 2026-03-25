from financial_report_decode.services.report_value import ReportValueAssessor


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
