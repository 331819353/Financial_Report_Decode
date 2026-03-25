from financial_report_decode.services.report_value import ReportValueAssessor


def test_value_assessor_high_value() -> None:
    markdown = """
# 标题
## 公司概况
2025年上半年公司收入123，利润456。
## 经营表现
收入增长12%，销量增长8%。
## 盈利能力
毛利率30%，净利率10%。
## 现金流或资产负债
经营现金流789，资产负债率40%。
## 风险与展望
原材料波动、需求承压，但新产品推进。
- 洞察1
- 洞察2
- 洞察3
"""
    result = ReportValueAssessor().assess(markdown)
    assert result.is_valuable is True
    assert result.score >= 80
