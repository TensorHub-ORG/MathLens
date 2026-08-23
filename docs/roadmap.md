# MathCraft 路线图

路线图按可验证的产品闭环推进。日期不是完成标准，退出条件才是。

## M0：Core Foundation

状态：已完成

范围：

- Python/uv 项目环境；
- MathIR 初始领域模型；
- PDF 基础探测；
- CLI 和质量工具；
- 文本与公式评测骨架；
- 产品愿景和架构边界。

退出条件：

- 测试、Ruff 和 mypy strict 通过；
- 真实样例 PDF 可产生可追溯 profile；
- 后续功能可以明确归入 Core、Flow、Skill、Adapter 或 Verifier。

## M1：Ingestion Baseline

状态：已完成

阶段进度：

- M1-A 页面渲染与 artifact：已完成；
- M1-B 代表页选择、Golden Schema、评测器与本地标注工作台：已完成，12 页版面与阅读顺序
  均已验证；
- M1-C MinerU Adapter：3.4.5 的 12 个代表页预测均已生成，CUDA Pipeline、设备诊断和
  Windows 子进程回收已完成；
- M1-D Content Golden & Parsing Baseline：已完成。29/29 个公式 block 与 47/228 个文本
  block 已人工复核，首份可复现的 MinerU 3.4.5 管线校准基线已经冻结。

范围：

- 页面高分辨率渲染；
- 页面图和裁剪图 artifact；
- 扫描、矢量和混合页面分类；
- MinerU 适配器；
- 从真实试卷抽取分层 golden set；
- 文本、公式、版面和阅读顺序基线。

退出条件：

- 从目标 PDF 选定至少 10 个代表性页面；
- 每个识别 block 可以回到原页坐标和裁剪图；
- 基线报告可在同一锁定环境中复现；
- 替换解析器不改变 MathIR 消费方。

M1-D 已将 M1-A 至 M1-C 的产物转化为有明确人工证据、覆盖率和复现条件的基线。结果与
辅助标注限制见[首份 M1 解析基线](baselines/mineru-3.4.5-m1.md)。下一阶段为 M2。

## M2：LaTeX Reconstruction

范围：

- 试卷、题目和小题结构；
- 可维护 LaTeX AST 或结构化生成；
- XeLaTeX/LuaLaTeX 编译；
- 公式局部重识别；
- 编译、视觉和符号一致性诊断；
- 低置信 block 人工复核数据模型。

退出条件：

- golden 页面可生成可编译 LaTeX；
- 原始转录与规范化内容严格分离；
- 对 `A^T`/`A^7` 一类可编译错误能给出失败证据；
- 修改后的 block 保留完整来源和审计记录。

## M3：Internal Skills

范围：

- 最小工作流执行上下文；
- Academic Translation 内部 Skill；
- Proof Verification 内部 Skill；
- 类型化输入输出和分级验证报告；
- Agent 与确定性 Verifier 分离。

退出条件：

- 两个 Skill 在相同执行模型中运行；
- Skill 无需直接访问 Core 内部对象；
- 网络、文件和进程权限可以声明并审计；
- 能从真实实现中识别稳定的 SDK 公共部分。

## M4：Skill Runtime and SDK

范围：

- Skill Manifest v1；
- Python SDK 和脚手架；
- 安装、启用、禁用和版本解析；
- sidecar 隔离、资源限制和取消；
- conformance test kit；
- Workflow DAG、缓存和恢复。

退出条件：

- 第三方示例 Skill 不修改 Core 即可安装；
- 不兼容的 Schema 或 API 版本被明确拒绝；
- 失败、超时和取消不会污染已有 artifact；
- 插件权限在执行前对用户可见。

## M5：MathCraft Studio

范围：

- Tauri 桌面应用；
- 页面、block、公式候选和结构树联动；
- 人工复核工作台；
- 编译预览和差异视图；
- 本地工作流管理；
- 可选本地或远程推理后端。

退出条件：

- 用户可以在不使用命令行的情况下完成 M2 闭环；
- 桌面层不包含解析和推理核心逻辑；
- 长任务可以恢复、取消并查看完整诊断。

## M6：Community Ecosystem

前置条件：公开许可证和治理模式已经确定。

范围：

- 官方 Skill 索引；
- 安全审查和包签名；
- 兼容性与维护状态；
- 社区模板和贡献流程；
- 可选 MathCraft Hub。

Marketplace、复杂多 Agent 编排和分布式执行在有真实需求之前不进入实现计划。
