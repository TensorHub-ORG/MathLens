# MathLens 架构原则

状态：Active
最后更新：2026-08-22

## 架构目标

MathLens 采用稳定核心、显式边界、不可变 artifact 和可验证工作流。架构首先服务于正确性、
可维护性和可复现性，其次才是扩展数量。

## 概念词汇

| 概念 | 定义 | 示例 |
|---|---|---|
| Node | 最小可执行操作 | 渲染页面、编译 TeX |
| Adapter | 外部引擎的技术适配 | PyMuPDF、MinerU、模型 API |
| Verifier | 产生确定性验证证据 | Lean Kernel、LaTeX 编译器 |
| Agent | 使用模型完成不确定推理 | 题目切分、解题、形式化 |
| Skill | 面向用户目标的能力包 | 学术翻译、证明验证 |
| Workflow | Node 和 Skill 构成的有向任务图 | 扫描试卷重构 |
| Plugin | 安装、隔离和发布单位 | 包含一个或多个 Skill 的包 |
| Artifact | 不可变、可寻址的执行输入或输出 | 页面图、MathIR、TeX、报告 |

多 Agent 是 Workflow 的一种执行策略，不是基础架构层，也不是 Skill 的必要条件。

## 分层与依赖方向

```text
Interfaces (CLI / API / Studio)
              ↓
Application (use cases / workflows)
              ↓
Ports (contracts)
              ↓
Domain (MathIR / invariants)

Adapters implement Ports and may depend on Domain.
Domain never imports Adapters, CLI, model SDKs, or workflow runtimes.
```

当前源码结构：

```text
src/mathlens/
├── domain/       # MathIR、值对象和不变量
├── ports/        # 解析器、存储、编译器等协议
├── adapters/     # PyMuPDF、MinerU 和外部运行时实现
├── application/  # 用例编排，不依赖具体 UI
├── evaluation/   # 评测数据结构和指标
├── golden/       # Golden Schema 与验证不变量
├── studio/       # 本地 Workbench 服务边界
└── cli.py        # 当前接口层
```

新模块必须由真实用例驱动，不创建没有调用方的抽象层。

## 长期目标架构

```text
Mathematical Information Containers
PDF · Image · TeX · Markdown · HTML · Office · Handwriting · Lean source
                              │
                    Document Adapters
          MinerU · PyMuPDF · future parsers/importers
                              │
                              ▼
┌────────────────────── MathLens Core ──────────────────────┐
│       MathIR contracts · Artifact DAG · Provenance         │
│       Schema registry · Evaluation · Capability ports      │
└────────────────────────────┬───────────────────────────────┘
                             │ typed artifacts
                             ▼
┌────────────────────── MathLens Flow ──────────────────────┐
│ state graph · checkpoint · retry · cache · HITL · policy  │
└───────────────┬────────────────┬────────────────┬──────────┘
                │                │                │
        Understanding       Reasoning       Verification
        OCR / structure     solve / prove    evidence / kernel
        MinerU / PyMuPDF    model / agents   Lean / CAS / tests
                └────────────────┼────────────────┘
                                 ▼
                      Output / Knowledge Skills
                  LaTeX · search index · study material
```

MathIR 是数据平面的核心；Flow 是调度和控制平面。Flow 只能通过版本化 artifact 与节点通信，
不能把某个 Agent 框架的私有 state 当作长期数据协议。Skills 是能力与分发层，可以跨越理解、
推理、验证和输出阶段，但不能绕过 Core 的来源与证据约束。

### LangGraph 的位置

MathLens Flow 借鉴 [LangGraph](https://github.com/langchain-ai/langgraph) 的状态图、持久化
checkpoint、可恢复执行和人工中断思想。未来
可以提供 LangGraph-backed runtime，但 LangGraph 不是架构层，也不进入 MathIR 或 Domain。
Flow 首先冻结自己的 Node、Run、Checkpoint、Interrupt 和 Artifact 契约，再决定内部执行器。
这使未来可以替换为自研运行时、任务队列或其他图执行引擎。

可视化工作流可借鉴 Dify、ComfyUI 等产品的节点编辑体验；画布 Schema 同样只描述 MathLens
Workflow，不直接保存第三方运行时对象。

## MathIR 原则

- MathIR 是项目内部规范，不直接等同于 MinerU 或任何供应商输出；
- 所有实体使用稳定 ID；
- 坐标必须声明坐标空间；
- 页面和 block 保留原始顺序，但文档逻辑关系单独表达；
- 候选内容记录引擎、版本和置信度；
- 原始转录、规范化内容和生成内容使用不同字段或 artifact；
- Schema 发生破坏性变化时提升版本，不编写无限期兼容旧格式的兜底逻辑。

MathIR 采用一个版本化 artifact envelope，并提供相互关联的投影，避免形成一个无限膨胀的
单体 JSON：

| 投影 | 负责内容 |
|---|---|
| Source/Document | 原始容器、页面、几何、阅读顺序、裁剪图和候选转写 |
| Semantic | 符号、表达式、定义、命题、假设、题目和引用关系 |
| Reasoning | claim、推理步骤、分支、依赖、生成来源和不确定性 |
| Verification | 被验证对象、方法、工具链、假设、日志、反例和证据等级 |
| Presentation | LaTeX、Markdown、HTML、图形和其他可再生成输出 |

投影可以独立生成和版本化，通过稳定 ID 与父 artifact 关联。原始转写永远不会被语义规范化、
模型解答或形式化翻译覆盖。

## 外部项目的正确边界

| 项目 | 可借鉴或接入的能力 | 在 MathLens 中的位置 |
|---|---|---|
| MinerU / PyMuPDF | 容器解析、OCR、页面与布局 | Document Adapter |
| [Danus](https://github.com/frenzymath/Danus) | 长程多 Agent、事实图、独立 verifier gate | Research Reasoning Skill / 参考架构 |
| [frenzymath/Archon](https://github.com/frenzymath/Archon) | plan/prover/review 循环、多 harness 长程执行 | Research Reasoning Skill / Flow 实验后端 |
| [ScalingIntelligence/Archon](https://github.com/ScalingIntelligence/Archon) | generator/critic/ranker/fuser 等推理时组合与搜索 | Reasoning Strategy Skill |
| [OpenProof](https://github.com/mxthematic/openproof) | 自然语言到 Lean、Agent 与 tactic search 协作 | Formalization + Proof Search Skill |
| [LeanDojo-v2](https://github.com/lean-dojo/LeanDojo-v2) | Lean 数据提取、训练、检索和证明搜索 | Prover Adapter / Research Skill |
| [Lean 4 Kernel](https://github.com/leanprover/lean4) | 对形式化命题和证明项做确定性检查 | Verifier、最终信任边界 |

同名 Archon 必须在 manifest 中使用不同 provider/skill ID，不能只以显示名称解析。Danus、
Archon 和 OpenProof 都不进入 Core 依赖；验证 Skill 即使使用它们生成证明，最终证据仍必须包含
Lean 工具链、Mathlib revision、命题、假设和内核检查结果。

## Artifact 原则

Artifact 一旦发布即不可变。更新意味着产生新 artifact，并记录父级关系。

最低元数据包括：

```text
artifact_id
schema
content_hash
parents
stage
engine
engine_version
configuration_hash
created_at
diagnostics
```

大型二进制内容保存在 artifact store，工作流只传递引用。用户源文件、模型缓存和运行产物
不进入源码仓库。

页面渲染 artifact 的寻址、隐私和坐标约定见
[ADR-0002](decisions/0002-content-addressed-page-artifacts.md)。

## 工作流原则

- 确定性操作优先使用普通 Node；
- Agent 只处理需要语义判断或开放式推理的节点；
- Verifier 与生成答案的 Agent 分离；
- 每个节点声明输入、输出、超时、权限和资源；
- 节点失败必须返回结构化诊断；
- 支持按 artifact hash 缓存和从失败节点恢复；
- 人工审核是一等节点，而不是异常兜底。

## Skill 边界

Skill 是长期方向，当前尚未冻结 SDK。只有在至少两个内部 Skill 被真实实现后，才从共同需求
中提取公开协议。首选验证样本为：

- Academic Translation：模型驱动、保留公式和术语一致性；
- Proof Verification：Agent 形式化、工具搜索、Lean 确定性检查和分级报告。

未来 Skill Manifest 至少需要声明：

- 唯一 ID、版本、API 版本和许可证；
- 版本化输入输出 Schema；
- 执行方式和入口；
- 文件、网络、进程等权限；
- CPU、内存、GPU 和超时；
- 外部运行时和模型依赖；
- 测试、示例和兼容范围。

## 安全与隐私

- 默认本地处理和默认拒绝网络；
- 原始用户文件只通过显式 artifact capability 暴露；
- Skill 不直接获得任意文件系统访问；
- 外部进程采用独立工作目录并限制生命周期；
- 远程模型调用记录服务、模型和发送的数据范围；
- 日志不得包含完整用户文档或凭证；
- Marketplace 建设前必须具备权限审查、包签名和撤销机制。

## 质量门

每个适配器和 Skill 都必须有与其风险相称的测试：

- Domain：不变量与序列化测试；
- Adapter：契约测试和真实小样本；
- OCR/解析：golden regression；
- LaTeX：编译与渲染测试；
- Verifier：成功、失败、超时和错误假设；
- Workflow：恢复、缓存、取消和 provenance；
- Skill：Schema、权限和端到端样例。

评测指标与模型输出共同版本化。不能用新指标重新解释旧结果而不留下记录。
