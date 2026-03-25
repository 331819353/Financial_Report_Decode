# Financial Report Decode

基于 Python 的财报解读项目。用户仅输入 `股票编码 + 财报日期`，系统会：

1. 先从本地指标接口提取公司基础指标，生成初步结论。
2. 通过 HTTP 下载 PDF 财报并抽取文本。
3. 以“自身 20000 字符 + 上文 1000 + 下文 1000”的滑动窗口方式逐块分析。
4. 对当前财报解读结果进行“是否具备分析价值”的判断。
5. 若价值不足，再调用网络检索补充外部信息并生成最终 Markdown 报告。
6. 若 PDF 文字层缺失或乱码比例过高，自动启用 OCR 兜底抽取。

## 目录结构

```text
src/financial_report_decode/
  clients/      # 外部接口与模型调用
  services/     # 编排、切块、价值判断、报告生成
  utils/        # Markdown 等通用工具
  main.py       # CLI 入口
```

## 快速开始

### 1. 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. 配置环境变量

可参考 `.env.example`：

```bash
cp .env.example .env
```

关键配置：

- `ALIYUN_IQS_BEARER_TOKEN`: 网络检索接口 Bearer Token
- `DASHSCOPE_API_KEY`: 百炼兼容接口 API Key
- `PDF_DOWNLOAD_ENDPOINT`: 正式财报下载接口
- `PDF_DOWNLOAD_URL_TEMPLATE`: 若正式接口不适用时的备用模板 URL
- `PDF_OCR_ENABLED`: 是否启用 OCR 兜底
- `PDF_OCR_DPI`: OCR 渲染精度

正式接口默认使用：

```text
https://hgpmp.haier.net/cgapi3/dmzlyyextinfo/downFile
```

请求方式：

- `GET`
- Query 参数：`stockCode`、`reportDate`

备用模板 `PDF_DOWNLOAD_URL_TEMPLATE` 示例：

```text
https://example.com/reports/{stock_code}/{report_title}
```

可用变量：

- `{stock_code}`
- `{report_date}`
- `{year}`
- `{quarter}`
- `{company_name}`
- `{report_title}`

### 3. 运行

```bash
financial-report-decode \
  --stock 002508.SZ \
  --date 2025-06-30 \
  --keyword 营业收入
```

若已有财报直链，也可以直接指定：

```bash
financial-report-decode \
  --stock 002508.SZ \
  --date 2025-06-30 \
  --pdf-url "https://example.com/xxx.pdf"
```

若要直接用本地 PDF 和数据库返回 JSON 验证流程：

```bash
financial-report-decode \
  --stock 1070.HK \
  --date 2025-06-30 \
  --pdf-path "/Users/susanmartinez/Downloads/1070.HK+2025Q2.pdf" \
  --snapshot-file "examples/tcl_1070_hk_2025h1_snapshot.json" \
  --mock-llm \
  --skip-network-search \
  --output validation_output
```

输出文件默认写入 `reports/` 目录。

## OCR 增强

项目内置开源免费 OCR 兜底能力：

- `PyMuPDF`：负责把 PDF 页面渲染成图像
- `RapidOCR`：优先使用，适合支持的 Python 环境
- `ocrmac`：macOS 下自动回退到 Apple Vision OCR

触发条件：

1. 原始 PDF 抽取文本为空。
2. 原始文本长度过短。
3. 原始文本乱码比例过高。

这能改善扫描版财报、图片版财报和文字层质量较差的 PDF。

## 价值判断标准

系统会判断分析结果是否达到“可交付”标准，判定维度包括：

1. 是否覆盖公司概况、经营表现、盈利能力、现金流/资产负债、风险与展望。
2. 是否给出量化指标或趋势描述，而不是只有泛泛表述。
3. 是否提炼出至少 3 条具备业务洞察或投资分析意义的结论。
4. 是否说明关键信息来源是财报原文、基础指标或网络检索补充。

若未达标，会自动触发网络检索增强。

## 说明

- 未将任何密钥硬编码进仓库。
- 网络检索与模型接口遵循你提供的参考代码逻辑。
- 正式 PDF 下载已按 `https://hgpmp.haier.net/cgapi3/dmzlyyextinfo/downFile?reportDate=...&stockCode=...` 实现。
