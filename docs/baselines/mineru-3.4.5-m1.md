# MinerU 3.4.5 M1 解析基线

状态：Completed
日期：2026-08-22

## 结论

M1 已完成扫描 PDF 到可审计解析结果的首个闭环。本报告冻结的是 MathLens 解析、Golden
复核与评测管线的校准基线，不是 MinerU 的独立精度声明。

## 数据与环境

- 数据集：`high-algebra-2022-2024-seed`；
- 源文件 SHA-256：`447ae6c65dfbdbfc391dc028b18d3c93c729e2b6012e163891cffea68e18a893`；
- 代表页：1、7、12、30、50、70、90、110、130、150、170、207，共 12 页；
- 页面渲染：PyMuPDF，300 DPI，内容寻址 artifact；
- 解析器：MinerU 3.4.5，`pipeline / ocr / ch`，以 CUDA 批量解析为主；
- Golden Schema：`mathlens.golden-dataset.v3`；
- Evaluation Schema：`mathlens.parsing-evaluation.v2`；
- 匹配阈值：IoU 0.5。

原始 PDF、页面图和模型输出位于本地 `workspace/`，不进入仓库。代表页选择清单、Golden
Schema、评测实现和两套 uv 锁文件进入版本控制。

## 人工证据覆盖率

| 维度 | 已复核 | 可复核 | 覆盖率 |
|---|---:|---:|---:|
| 页面版面 | 12 | 12 | 100% |
| 阅读顺序 | 12 | 12 | 100% |
| 公式内容 | 29 | 29 | 100% |
| 文本转写 | 47 | 228 | 20.6% |

公式采用全量复核；文本通过稳定哈希抽样和风险队列复核，覆盖率高于 M1 约定的 10%。

## 评测结果

| 指标 | 结果 |
|---|---:|
| Layout precision / recall / F1 | 0.9961 / 0.9961 / 0.9961 |
| Mean IoU | 0.9995 |
| Block type accuracy | 1.0000 |
| Reading-order accuracy | 1.0000 |
| 文本 CER（47 个样本） | 0.1288 |
| 公式精确匹配率（28 个匹配样本） | 0.8929 |

257 个 Golden block 中有 256 个与预测匹配。1 个已复核公式 block 未匹配，因此公式内容
覆盖率为 29/29，但可计分样本为 28；缺失预测已经通过 layout recall 反映，不能伪造公式内容
比较结果。

## 解释边界

本批 Golden block 全部由 MinerU 3.4.5 建议初始化，再由人工逐维复核。评测报告会披露
`assisted_reference_blocks = 257`。因此：

- 这组结果证明坐标映射、来源追踪、复核状态和评测计算能够形成稳定闭环；
- 内容指标可以作为同一数据、同一协议下的后续回归锚点；
- 版面与顺序的高分不能当作 MinerU 在独立盲测集上的泛化精度；
- M2 或解析器横向比较前，应新增独立标注或双人仲裁的小型盲测集。

## 复现

先按 `benchmarks/high-algebra-2022-2024/selection.json` 准备同一源 PDF 与 12 份 MinerU
MathIR 预测，然后运行：

```powershell
.tools\uv run mathlens golden-validate workspace\golden\reference.json

.tools\uv run mathlens evaluate-parsing workspace\golden\reference.json `
  workspace\mineru-page-1\mathlens-parse-result.json `
  workspace\mineru-page-7-retry\mathlens-parse-result.json `
  workspace\mineru-page-12\mathlens-parse-result.json `
  workspace\mineru-page-30\mathlens-parse-result.json `
  workspace\mineru-page-50\mathlens-parse-result.json `
  workspace\mineru-page-70\mathlens-parse-result.json `
  workspace\mineru-page-90\mathlens-parse-result.json `
  workspace\mineru-page-110\mathlens-parse-result.json `
  workspace\mineru-page-130\mathlens-parse-result.json `
  workspace\mineru-page-150\mathlens-parse-result.json `
  workspace\mineru-page-170\mathlens-parse-result.json `
  workspace\mineru-page-207\mathlens-parse-result.json `
  --verified-only --output workspace\evaluations\mineru-3.4.5-m1-final.json
```

运行环境由根目录 `uv.lock` 与 `integrations/mineru/uv.lock` 分别锁定。生成报告应与本文的
样本数和汇总指标一致。
