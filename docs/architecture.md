# MathLens 架构原则

状态：Active
最后更新：2026-08-21

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
├── adapters/     # PyMuPDF、未来的 MinerU 等实现
├── evaluation/   # 评测数据结构和指标
└── cli.py        # 当前接口层
```

当真实用例出现后再增加 `application/` 和 `artifacts/` 模块，不创建没有调用方的抽象层。

## MathIR 原则

- MathIR 是项目内部规范，不直接等同于 MinerU 或任何供应商输出；
- 所有实体使用稳定 ID；
- 坐标必须声明坐标空间；
- 页面和 block 保留原始顺序，但文档逻辑关系单独表达；
- 候选内容记录引擎、版本和置信度；
- 原始转录、规范化内容和生成内容使用不同字段或 artifact；
- Schema 发生破坏性变化时提升版本，不编写无限期兼容旧格式的兜底逻辑。

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
