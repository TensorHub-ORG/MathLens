# Golden Dataset 工作流

MathLens 的解析质量由版本化 golden dataset 衡量。选择页面、人工标注和引擎预测必须分离，
不能把 MinerU 或其他模型的输出直接当作真值。

## Seed Selection

首个真实样本清单位于
[`benchmarks/high-algebra-2022-2024/selection.json`](../benchmarks/high-algebra-2022-2024/selection.json)。
它只记录源文件名、SHA-256、页码、分层标签与选择理由，不提交受版权保护的 PDF 或页面图。

12 个页面覆盖目录、密集正文、跨试卷边界、矩阵、行列式、分段方程组、并排布局、水印和
稀疏页。页面必须按 300 DPI 渲染后，在本地 `workspace/` 中完成标注。

生成本地标注模板与页面 artifact：

```powershell
mathlens golden-prepare benchmarks\high-algebra-2022-2024\selection.json source.pdf \
  --artifact-dir workspace\golden\artifacts \
  --output workspace\golden\reference.json
```

命令会先校验源 PDF 的 SHA-256，再按清单 DPI 渲染，并将页面 artifact ID 写入模板。

## Schema

`mathlens.golden-dataset.v3` 使用 0..1000 归一化坐标。每个 block 包含：

- 稳定且页内唯一的 `id`；
- MathIR `BlockType`；
- `bbox`；
- 可选的 `source_transcription`；
- 可选且与原文转写分离的 `latex`；
- 可选的结构化 `suggested_by`，记录辅助标注所采用的引擎、版本、配置哈希与原 block ID；
- 可选的标注说明。
- block 级 `verified_aspects`，只记录该块实际完成的 `transcription` 或 `formula` 人工复核。

页面显式保存 `reading_order`，页面级 `verified_aspects` 只记录 `layout` 和 `reading_order`；
内容证据记录在 block 上。正式评测只计算已经人工验证的 block；布局未验证的页面不会进入评测。
这样，检查框与顺序不会被误报为 OCR 或公式真值，内容复核也可以使用风险队列和抽样策略逐步完成。

## 指标

`evaluate-parsing` 在可配置的 IoU 阈值下报告：

- layout precision、recall、F1 和 mean IoU；
- block type accuracy；
- 阅读顺序的成对一致率；
- 文本字符错误率（CER）；
- 基于 `latex` 字段、忽略空白差异后的公式精确匹配率；
- 来自解析器建议层的 reference block 数量，用于识别辅助标注导致的评测泄漏。

接受模型建议并完成人工复核仍属于辅助标注。使用同一引擎的建议初始化 Golden，再评测该
引擎时，报告中的 `assisted_reference_blocks` 会披露这种来源重合；此类结果可以验证评测管线，
但不能作为独立的解析精度基线。

在分阶段复核期间，可以同时合并多个单页预测，并只评测已经复核的页面：

```powershell
mathlens evaluate-parsing workspace\golden\reference.json `
  workspace\mineru-page-7\mathlens-parse-result.json `
  workspace\mineru-page-12\mathlens-parse-result.json `
  --verified-only --output workspace\evaluations\mineru-initial.json
```

首版匹配采用按 IoU 从高到低的一对一贪心匹配。指标算法与报告 Schema 都必须随代码版本化，
未来替换匹配算法时需要新增 ADR 或提升评测 Schema。

## Golden Workbench

本地标注工作台负责显示页面 artifact、只读模型建议和可编辑人工真值。模型建议只有经过
用户接受后才成为 Golden block，并保留 `suggested_by` 来源；接受动作不等于人工复核。

安装并构建前端：

```powershell
cd studio
npm ci
npm run build
cd ..
```

启动第一个真实工作区：

```powershell
mathlens golden-studio workspace\golden\reference.json `
  --artifact-dir workspace\golden\artifacts `
  --prediction workspace\mineru-page-7-retry\mathlens-parse-result.json
```

服务只监听用户显式指定的本地地址，默认是 `127.0.0.1:8765`。保存请求携带数据集修订哈希；
如果磁盘文件已被其他进程修改，工作台会拒绝覆盖并要求重新载入。页面更新通过同目录临时
文件原子替换写入。

工作台会并排呈现原图裁剪与公式渲染，并把全部公式、缺失内容、语法风险以及按稳定哈希选出的
10% 文本样本加入内容复核队列。逐块确认后自动前往下一项，避免重复检查整页。
任何修改只撤销受影响维度的验证；例如重排 block 只撤销 `reading_order`，不会要求重复检查版面。

## 人工复核策略

人工不需要在每次解析时逐页重复确认。首个版本与引擎大版本升级时建立完整校准集；日常回归只
全量复核风险队列，并从无风险 block 中按页面分层抽样至少 10%。若抽样发现错误，则扩大该
错误类型和相邻层级的复核范围。只有实际人工确认过的维度才能加入 `verified_aspects`；自动
规则可以决定“先看哪里”，不能把同一解析器的输出自动升级为内容真值。

M1 已冻结的首次校准结果见
[MinerU 3.4.5 M1 解析基线](baselines/mineru-3.4.5-m1.md)。
