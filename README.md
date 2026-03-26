# Financial Report Decode

基于 Python 的财报解读项目。用户仅输入 `股票编码 + 财报日期`，系统会：

1. 先从本地指标接口提取公司基础指标，生成初步结论。
2. 通过 HTTP 下载 PDF 财报并抽取文本。
3. 以“自身 20000 字符 + 上文 1000 + 下文 1000”的滑动窗口方式逐块分析。
4. 对当前财报解读结果进行“是否具备分析价值”的判断。
5. 若价值不足，再调用网络检索补充外部信息并生成最终 Markdown 报告。
6. 在详报生成完成后，复用前序结果继续提炼简报，并执行独立审核。
7. 详报与简报写入同一张 MySQL 表，详报使用 `conclusion` 字段，简报使用 `summary` 字段。
8. 若 PDF 文字层缺失或乱码比例过高，自动启用 OCR 兜底抽取。

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

正式运行时，实际入参只有：

- `stock_code`
- `report_date`

也就是命令行里的：

- `--stock`
- `--date`

`--pdf-path`、`--snapshot-file`、`--mock-llm`、`--skip-network-search` 仅用于联调、测试或离线验证，不属于正式生产入参。

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Windows

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

如果 PowerShell 默认禁止脚本执行，可先执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2. 配置环境变量

可参考 `.env.example`：

```bash
cp .env.example .env
```

关键配置：

- `ALIYUN_IQS_BEARER_TOKEN`: 网络检索接口 Bearer Token
- `LLM_API_KEY` 或 `MGALLERY_API_KEY`: DeepSeek v3 接口 API Key
- `LLM_BASE_URL` 或 `MGALLERY_BASE_URL`: 模型网关地址，默认 `https://mgallery.haier.net/v1`
- `LLM_MODEL`: 默认 `deepseek-v3`
- `PDF_DOWNLOAD_ENDPOINT`: 正式财报下载接口
- `REPORT_DB_HOST` / `REPORT_DB_PORT` / `REPORT_DB_USER` / `REPORT_DB_PASSWORD` / `REPORT_DB_NAME`: 报告写入 MySQL 配置
- `REPORT_DB_TABLE`: 报告落库表名，默认 `caibao_financial_reports`
- `PDF_OCR_ENABLED`: 是否启用 OCR 兜底
- `PDF_OCR_DPI`: OCR 渲染精度
- `PDF_TESSERACT_CMD`: Windows/Linux 下 `tesseract.exe` 或 `tesseract` 的路径

正式接口默认使用：

```text
https://hgpmp.haier.net/cgapi3/dmzlyyextinfo/downFile
```

请求方式：

- `GET`
- Query 参数：`stockCode`、`reportDate`

### 3. 运行

正式生产运行：

```bash
financial-report-decode \
  --stock 002508.SZ \
  --date 2025-06-30
```

若需要输出详细日志：

```bash
financial-report-decode \
  --stock 002508.SZ \
  --date 2025-06-30 \
  --show-logs
```

仅用于联调验证的本地文件模式：

```bash
financial-report-decode \
  --stock 1070.HK \
  --date 2025-06-30 \
  --pdf-path "/Users/susanmartinez/Downloads/1070.HK+2025Q2.pdf" \
  --snapshot-file "examples/tcl_1070_hk_2025h1_snapshot.json" \
  --mock-llm \
  --show-logs
```

输出文件默认写入 `reports/` 目录，并同时生成：

- 详报：`{stock}_{date}_dr_analysis.md`
- 简报：`{stock}_{date}_br_analysis.md`

数据库写入规则：

- 详报：`report_type=DR`，内容写入 `conclusion`
- 简报：`report_type=BR`，内容写入 `summary`
- 两类报告写入同一张表 `caibao_financial_reports`

## OCR 增强

项目内置开源免费 OCR 兜底能力：

- `PyMuPDF`：负责把 PDF 页面渲染成图像
- `RapidOCR`：Windows/Linux/macOS 优先使用，适合支持的 Python 环境
- `ocrmac`：macOS 下自动回退到 Apple Vision OCR
- `pytesseract`：跨平台兜底，适合已安装 `tesseract` 的环境

触发条件：

1. 原始 PDF 抽取文本为空。
2. 原始文本长度过短。
3. 原始文本乱码比例过高。

这能改善扫描版财报、图片版财报和文字层质量较差的 PDF。

OCR 后端选择顺序：

1. `RapidOCR`
2. `ocrmac`（仅 macOS）
3. `pytesseract`

若在 Windows 上部署，建议优先安装 `RapidOCR`；若环境是 Python 3.13 或无法安装 `RapidOCR`，则安装系统级 `Tesseract OCR` 并配置 `PDF_TESSERACT_CMD`。

Windows 安装 `Tesseract OCR` 后，建议把安装目录加入 `PATH`，或在 `.env` 中设置：

```text
PDF_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## 价值判断标准

系统会判断分析结果是否达到“可交付”标准，判定维度包括：

1. 是否覆盖公司概况、经营表现、盈利能力、现金流/资产负债、风险与展望。
2. 是否给出量化指标或趋势描述，而不是只有泛泛表述。
3. 是否提炼出至少 3 条具备业务洞察或投资分析意义的结论。
4. 是否说明关键信息来源是财报原文、基础指标或网络检索补充。

若未达标，会自动触发网络检索增强。

## 说明

- 未将任何密钥硬编码进仓库。
- 模型默认已切换为 DeepSeek v3。
- 网络检索与模型接口遵循你提供的参考代码逻辑。
- 正式 PDF 下载已按 `https://hgpmp.haier.net/cgapi3/dmzlyyextinfo/downFile?reportDate=...&stockCode=...` 实现。
- 正式运行场景只需要 `stock_code` 与 `report_date` 两个入参。
- 当前主流程会同时产出详报与简报，并分别以 `DR`、`BR` 落库。
