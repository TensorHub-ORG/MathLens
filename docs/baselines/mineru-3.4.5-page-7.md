# MinerU 3.4.5 单页 Smoke Baseline

状态：Completed
日期：2026-08-21

## 输入与配置

- 源文件 SHA-256：`447ae6c65dfbdbfc391dc028b18d3c93c729e2b6012e163891cffea68e18a893`
- PDF 页码：7（MathLens 采用 1 起始页码）
- MinerU：3.4.5
- Backend：`pipeline`
- Method：`ocr`
- Language：`ch`
- Torch：2.13.0 CPU
- MathLens configuration hash：`703747d4d5638a96d78901dc62a7599f1cc41fa56cf89ff7dc4a261153aebde5`

## 结构结果

- 27 个带 0..1000 bbox 的 MathIR block；
- 18 个文本 block；
- 5 个行间公式 block；
- 3 个标题 block；
- 1 个页码 block；
- 0 个因缺失或非法 bbox 被省略的 item。

MinerU `layout.pdf` 的框选位置与阅读顺序在该页视觉核验中整体合理。原始
`content_list_v2.json` 已成功转换为 MathIR，页码从 MinerU 的 0 起始范围正确还原为 MathLens
的第 7 页。

## 已观察到的内容错误

本次 smoke run 不是正式准确率报告。在人工 golden 标注完成前，不发布 CER、公式准确率或
layout F1。视觉与 Markdown 检查已发现：

- `f(a+b)` 附近出现错误字符和重音符号；
- `-I_n` 被识别成带异常重音的表达；
- 原页一个 3×3 对角矩阵在 Markdown 中被展开为 4×4；
- 部分中文标点、空格与题号风格发生规范化或误识别。

这些错误可能保持 LaTeX 可编译，却会改变数学含义，因此后续必须以人工复核的 golden
reference 评分，不能使用 MinerU 自身输出生成真值。

## 运行时发现

MinerU 3.4.5 的 `pipeline` OCR 路径导入 `six`，但官方 extra 未声明该包。MathLens 的隔离
运行时显式锁定 `six==1.17.0`，该补充只存在于 `integrations/mineru`，没有加入 Core 依赖。
