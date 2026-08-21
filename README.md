# MathLens

MathLens 是一个面向数学文档的开放、可验证、可扩展的智能处理与推理平台。

当前仓库首先建设稳定的 `MathLens Core`：把扫描 PDF 和图片转换为具有来源坐标、
候选结果与完整溯源信息的 MathIR，并为 OCR、LaTeX 重构、文档结构理解和质量评测
提供可靠基础。Agent、形式化验证和翻译等高级能力将在核心稳定后以 Skill 形式接入。

## 当前能力

- 数学文档中间表示 MathIR；
- 基于 PyMuPDF 的只读 PDF 探测；
- 带引擎、版本和置信度的内容候选；
- 文本字符错误率和保守的公式精确匹配评测；
- 可作为未来 Tauri sidecar 使用的 CLI；
- pytest、Ruff、mypy strict 质量门。

MinerU、GPU 模型和 Agent Runtime 不属于基础环境。它们将在建立真实基线和 golden
dataset 后，通过明确的端口和适配器接入。

## 项目文档

- [产品愿景](docs/product-vision.md)：使命、边界、原则和决策过滤器；
- [架构原则](docs/architecture.md)：Core、Runtime、Skill、Agent 与 Verifier 的职责；
- [路线图](docs/roadmap.md)：按可验收里程碑推进，而不是按功能清单堆叠；
- [贡献指南](CONTRIBUTING.md)：开发环境、质量要求和变更约束；
- [架构决策记录](docs/decisions/README.md)：记录重要且长期生效的技术决策。

上述文档是项目决策依据。代码实现与产品愿景冲突时，应先更新并评审文档，而不是在
代码中静默改变产品方向。

## 环境配置

项目使用 uv 管理 Python、依赖和锁文件。uv 二进制默认安装在项目内，避免污染系统环境：

```powershell
$env:UV_UNMANAGED_INSTALL = "$PWD\.tools"
irm https://astral.sh/uv/install.ps1 | iex
.tools\uv sync
```

## 常用命令

检查本地运行环境：

```powershell
.tools\uv run mathlens doctor
```

探测扫描或矢量 PDF：

```powershell
.tools\uv run mathlens inspect "path\to\document.pdf" --max-pages 10
```

运行 JSONL golden dataset 评测：

```powershell
.tools\uv run mathlens evaluate tests\fixtures\evaluation.jsonl
```

评测数据每行格式如下：

```json
{"id":"formula-001","kind":"formula","reference":"x^2+1","prediction":"x^2 + 1"}
```

## 开发检查

```powershell
.tools\uv run pytest --cov=mathlens --cov-report=term-missing
.tools\uv run ruff check .
.tools\uv run ruff format --check .
.tools\uv run mypy -p mathlens
```

运行产物放在 `artifacts/` 或 `workspace/`，两者均不进入版本控制。不要把原始 PDF、
模型权重、OCR 缓存或用户文档复制到源码目录。
