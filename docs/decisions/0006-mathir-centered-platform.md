# 0006：以 MathIR 为中心的平台架构

状态：Accepted
日期：2026-08-22

## 背景

MathLens 从扫描 PDF 解析起步，但数学信息还存在于图片、TeX、Markdown、网页、Office 文档、
手写材料和形式化源码中。长期还需要连接数学推理 Agent、符号系统、Lean 与社区 Skill。
如果以 PDF、某个 Agent 框架或某个模型作为中心，平台会随实现更换而反复重构。

## 决策

1. 将输入统一定义为 Mathematical Information Container；PDF 只是首个已实现容器。
2. MathIR、不可变 artifact DAG、来源追踪与验证证据构成 MathLens Core 的稳定数据平面。
3. MathLens Flow 是控制平面，调度类型化 Node/Skill；它借鉴 LangGraph，但不暴露第三方私有
   state 作为公共协议。
4. 理解、推理、验证和输出能力通过 Port、Adapter、Verifier 或 Skill 接入，不进入 Domain。
5. MathIR 使用关联投影表达文档、语义、推理、验证和呈现信息，不建设单体万能 Schema。
6. Lean Kernel 是形式化验证的信任边界；证明生成器和搜索框架只能产生候选与证据请求。
7. LLVM、VS Code 与 Git 仅作为稳定 IR、扩展协议和内容寻址 provenance 的设计参照。

## 后果

- 新容器或模型可以替换而不改变下游工作流契约；
- Flow 可以先自定义最小运行时，未来再接入 LangGraph 或其他执行器；
- Danus、两个不同的 Archon、OpenProof 与 LeanDojo-v2 可以作为实验 Skill/Adapter 比较；
- 需要逐步扩展 MathIR 语义与验证投影，并为每次扩展建立真实消费者和评测；
- MathLens 可以成长为数学智能基础设施，但不能在尚未实现时宣称等同于 LLVM、VS Code 或 Git。
