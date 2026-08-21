# 贡献指南

MathLens 当前处于 Core Foundation 阶段。贡献应优先提高真实数学文档处理的正确性、可追溯性
和可复现性，避免提前实现通用插件市场或多 Agent 框架。

## 开始之前

请先阅读：

1. [产品愿景](docs/product-vision.md)；
2. [架构原则](docs/architecture.md)；
3. [路线图](docs/roadmap.md)；
4. 与变更相关的 [架构决策记录](docs/decisions/README.md)。

如果变更会改变产品边界、公共 Schema、依赖方向或验证承诺，应先创建 ADR。

## 环境

```powershell
$env:UV_UNMANAGED_INSTALL = "$PWD\.tools"
irm https://astral.sh/uv/install.ps1 | iex
.tools\uv sync
```

## 必须通过的检查

```powershell
.tools\uv run pytest --cov=mathlens --cov-report=term-missing
.tools\uv run ruff check .
.tools\uv run ruff format --check .
.tools\uv run mypy -p mathlens
```

## 代码原则

- 优先清晰的小模块和显式类型；
- Domain 不依赖具体 OCR、模型 SDK、CLI 或 UI；
- 外部工具通过 Port 和 Adapter 接入；
- 不保留死函数、废弃分支和未经使用的抽象；
- 不为尚不存在的旧格式增加兼容兜底；
- 原始内容、规范化内容和生成内容不得混用；
- 错误必须结构化并包含足够诊断，不能静默吞掉；
- 修复缺陷时增加能够复现缺陷的测试；
- 模型或解析质量变化必须附带 golden evaluation。

## 数据与隐私

- 不提交用户 PDF、扫描图、模型权重或凭证；
- 测试夹具必须体积小、授权清晰并去除隐私信息；
- 大型或受版权保护的评测集只记录本地获取和校验方法；
- `artifacts/`、`workspace/`、`.uv-cache/` 和 `.venv/` 不进入版本控制。

## 依赖

新增运行时依赖需要说明：

- 它解决的具体问题；
- 为什么标准库或现有依赖不能满足；
- 许可证与分发限制；
- CPU、GPU、磁盘和网络成本；
- 如何测试和替换。

MinerU、Lean、LaTeX 发行版和模型运行时等重量级依赖应保持可选，并置于独立 Adapter、
Verifier 或 Skill 环境中。

## 提交和发布

除非项目所有者明确要求，不自动提交、推送、发布包或创建远程资源。

MathLens 采用 AGPL-3.0-only 与商业许可证双重授权。双重授权要求项目拥有对全部合并代码
进行商业再授权的权利。在律师审阅的 CLA 正式上线前，维护者不得合并不包含明确商业再
授权许可的外部代码。具体要求见[授权说明](docs/licensing.md)。

行为准则、安全响应流程和正式 CLA 仍需在公开接受社区贡献前完成。
