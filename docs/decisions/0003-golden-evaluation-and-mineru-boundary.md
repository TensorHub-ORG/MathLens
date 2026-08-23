# 0003：Golden 评测与 MinerU 接入边界

状态：Superseded by ADR 0005
日期：2026-08-21

## 背景

OCR 和公式识别输出可能在视觉上合理却改变数学含义。MinerU 3.x 提供统一的
`content_list_v2.json`，但官方仍将该格式标记为 development version。MathCraft 需要接入它，
同时避免让供应商 Schema、重量级模型依赖或模型自标注污染 Core 与评测真值。

## 决策

1. Golden reference 与 parser prediction 使用不同模型，任何引擎输出不得自动升级为真值。
2. Golden 页面只有达到 `reviewed` 或 `adjudicated` 状态后才能评分；评测器拒绝其他状态。
3. Block 使用 0..1000 归一化坐标，并显式记录页面阅读顺序。
4. 首版解析报告包含 layout precision/recall/F1、mean IoU、类型准确率、成对阅读顺序准确率、
   文本 CER 和公式精确匹配率。
5. MinerU Adapter 只消费官方 v3 `content_list_v2.json`，转换为 MathIR 后消费方不再读取
   MinerU 原始结构。
6. 缺少有效 bbox 的 item 产生结构化诊断并被省略，不猜测来源坐标。
7. MinerU 使用独立、锁定的 uv 子环境和外部进程；Core 不依赖 Torch、Transformers、ONNX
   Runtime 或 MinerU 包。
8. MinerU 输出格式发生破坏性变化时更新 Adapter 与契约测试，不保留无限期旧格式兜底。

## 后果

- 真实准确率报告需要人工标注成本；
- MinerU 可以替换而不改变 MathIR 或评测消费方；
- 模型版本、配置哈希、原始输出哈希和诊断可以追溯；
- `content_list_v2` 的上游变化会明确导致契约测试失败；
- 独立运行时增加一个锁文件，但避免污染轻量 Core 安装。

## 未选择的方案

### 用 MinerU 输出初始化并直接确认 Golden

会把系统性 OCR 错误写入真值，使指标失去意义。

### 在 Core 中直接导入 MinerU Python API

会把模型栈、平台差异和频繁变化的内部 API 绑定到 Core。

### 只评价 Markdown 是否生成

编译或生成成功无法发现矩阵维度、负号、上下标和量词等语义错误。
