# 架构决策记录

架构决策记录（ADR）用于保存影响多个模块、公共协议或长期维护方式的重要决定。ADR 记录
为什么这样做以及接受了哪些权衡，避免未来只看到代码结果却不知道原始约束。

## 何时创建 ADR

- 改变 MathIR 或其他公共 Schema；
- 引入新的重量级运行时；
- 改变 Core、Flow、Skill、Adapter 或 Verifier 边界；
- 引入外部进程、网络权限或插件执行机制；
- 选择会长期约束项目的存储、工作流或分发方案。

小型实现细节、容易撤销的局部重构和普通缺陷修复不需要 ADR。

## 状态

- Proposed：正在讨论；
- Accepted：当前生效；
- Superseded：已被新 ADR 替代；
- Rejected：经过讨论但未采用。

## 已有决策

- [0001：稳定核心与 Skill 边界](0001-stable-core-and-skills.md)
- [0002：内容寻址的页面图 Artifact](0002-content-addressed-page-artifacts.md)

## 模板

```markdown
# NNNN：决策标题

状态：Proposed
日期：YYYY-MM-DD

## 背景

## 决策

## 后果

## 未选择的方案
```
