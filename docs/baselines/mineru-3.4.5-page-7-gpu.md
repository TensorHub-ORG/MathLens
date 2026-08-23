# MinerU 3.4.5 第 7 页 CPU/GPU 对照

状态：Completed
日期：2026-08-22

## 环境与方法

- GPU：NVIDIA GeForce RTX 4050 Laptop GPU，6 GB；
- PyTorch：2.11.0+cu128；
- MinerU：3.4.5，`pipeline / ocr / ch`；
- 输入：同一 PDF 第 7 页；
- CPU 与 GPU 均通过同一 CUDA 运行时启动，唯一主动变量是 `device`；
- 每次调用均创建独立 MinerU CLI 进程，记录端到端耗时。

## 性能结果

| 运行 | 端到端耗时 | 说明 |
|---|---:|---|
| GPU 首次冷启动 | 101.570 s | CUDA DLL 与模型首次加载 |
| CPU 对照 | 91.803 s | 显式屏蔽 GPU |
| GPU 热基线 | 58.138 s | 相对 CPU 快约 1.58 倍 |

单页冷启动不保证 GPU 更快；批量工作流应复用服务或成批解析，摊薄模型启动成本。MathCraft
仍保留显式 CPU 模式，默认设备策略不能仅凭“存在 GPU”决定。

## 结构一致性

- CPU 与 GPU 都产生 27 个 block，bbox 完全一致，阅读顺序准确率均为 1.0；
- GPU 相对当前辅助 Golden 有 1 个 block 类型差异，类型准确率为 26/27；
- 另有 2 处文本空格差异；
- 当前页面仅验证 `layout` 与 `reading_order`，因此文本和公式样本数均为 0，不发布 CER 或
  公式精确率；
- 27 个 Golden block 均来自 MinerU 建议后人工检查，报告明确披露
  `assisted_reference_blocks = 27`，不能视为独立内容准确率结论。

## 运行时可靠性

Windows CLI 现在由 Job Object 托管。父任务正常结束、失败或超时后，临时 API 与模型 worker
都会被回收；真实 CPU/GPU 对照运行结束后均未留下 Python 子进程。
