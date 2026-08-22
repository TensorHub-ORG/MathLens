# MathLens

MathLens 是一个面向数学信息载体的开放、可验证、可扩展的智能处理与推理平台。PDF 是首个
输入形式，MathIR 才是连接解析、推理、验证、知识与输出能力的长期核心协议。

当前仓库首先建设稳定的 `MathLens Core`：把扫描 PDF 和图片转换为具有来源坐标、
候选结果与完整溯源信息的 MathIR，并为 OCR、LaTeX 重构、文档结构理解和质量评测
提供可靠基础。Agent、形式化验证和翻译等高级能力将在核心稳定后以 Skill 形式接入。

## M1 实际成果

首个里程碑已经完成从扫描 PDF、300 DPI 页面 artifact、MinerU GPU 解析，到块级 Golden
复核与可复现评测的完整闭环。Golden Annotation Workbench 支持页面与阅读顺序校验、
原图裁剪、KaTeX 公式对照、风险队列和稳定文本抽样。

![MathLens Golden Annotation Workbench](docs/assets/golden-workbench.png)

首份基线的适用范围、指标和辅助标注限制见
[MinerU 3.4.5 M1 解析基线](docs/baselines/mineru-3.4.5-m1.md)。

## 当前能力

- 数学文档中间表示 MathIR；
- 基于 PyMuPDF 的只读 PDF 探测；
- 基于 PyMuPDF 的高分辨率页面渲染；
- 内容寻址、可复现且带坐标映射的页面 artifact；
- 带引擎、版本和置信度的内容候选；
- 文本字符错误率和保守的公式精确匹配评测；
- 响应式 Golden Annotation Workbench；
- 隔离的 MinerU 3.4.5 CPU/CUDA 运行时；
- 可作为未来 Tauri sidecar 使用的 CLI；
- pytest、Ruff、mypy strict 质量门。

MinerU 和 GPU 模型通过独立适配器与隔离运行时接入，不属于 Core 基础环境。Agent Runtime
将在后续里程碑通过明确端口接入。

## 项目文档

- [产品愿景](docs/product-vision.md)：使命、边界、原则和决策过滤器；
- [架构原则](docs/architecture.md)：Core、Runtime、Skill、Agent 与 Verifier 的职责；
- [路线图](docs/roadmap.md)：按可验收里程碑推进，而不是按功能清单堆叠；
- [Golden Dataset](docs/golden-datasets.md)：代表页面、标注 Schema 与解析指标；
- [MinerU Adapter](docs/mineru.md)：独立运行时、导入与执行方式；
- [授权说明](docs/licensing.md)：AGPL 与商业许可证双重授权模式；
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

将指定页面以 300 DPI 渲染为不可变 artifact：

```powershell
.tools\uv run mathlens render "path\to\document.pdf" --page 1 --page 4 --output-dir artifacts
```

每个页面写入以 artifact ID 寻址的独立目录，其中包含 `page.png` 和 `manifest.json`。
manifest 记录源文件哈希、页码、DPI、像素尺寸、PDF 点坐标到像素坐标的映射、引擎版本
和配置哈希。省略 `--page` 时渲染全部页面；大型文档建议显式选择页面。

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

## Golden Annotation Workbench

构建独立前端并启动本地标注工作台：

```powershell
cd studio
npm ci
npm run build
cd ..

.tools\uv run mathlens golden-studio workspace\golden\reference.json `
  --artifact-dir workspace\golden\artifacts `
  --prediction workspace\mineru-page-7-retry\mathlens-parse-result.json
```

浏览器打开 `http://127.0.0.1:8765`。完整标注规则和复核门禁见
[Golden Dataset 文档](docs/golden-datasets.md)。

前端类型检查与浏览器交互测试：

```powershell
cd studio
npm run typecheck
npm run test:e2e
```

## 许可证

MathLens 采用双重授权：

- [GNU Affero General Public License v3.0 only](LICENSE)；或
- 由版权所有者张国人（Guoren Zhang）单独书面授予的[商业许可证](COMMERCIAL-LICENSE.md)。

闭源集成、私有修改、白标、OEM 及其他商业授权需求，请联系
[2245924824@qq.com](mailto:2245924824@qq.com)。详细说明见[授权文档](docs/licensing.md)。
