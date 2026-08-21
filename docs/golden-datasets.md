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

`mathlens.golden-dataset.v1` 使用 0..1000 归一化坐标。每个 block 包含：

- 稳定且页内唯一的 `id`；
- MathIR `BlockType`；
- `bbox`；
- 可选的 `source_transcription`；
- 可选的标注说明。

页面显式保存 `reading_order`。只有 `reviewed` 或 `adjudicated` 页面可以进入正式评测，且
阅读顺序必须包含页面的每个标注 block。`selected` 和 `draft` 只表示工作进度，评测器会拒绝
它们，防止把空模板误报为高分基线。

## 指标

`evaluate-parsing` 在可配置的 IoU 阈值下报告：

- layout precision、recall、F1 和 mean IoU；
- block type accuracy；
- 阅读顺序的成对一致率；
- 文本字符错误率（CER）；
- 忽略空白差异后的公式精确匹配率。

首版匹配采用按 IoU 从高到低的一对一贪心匹配。指标算法与报告 Schema 都必须随代码版本化，
未来替换匹配算法时需要新增 ADR 或提升评测 Schema。
