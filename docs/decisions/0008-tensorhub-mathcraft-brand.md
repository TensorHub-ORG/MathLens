# 0008：TensorHub MathCraft 品牌与子系统命名

状态：Accepted
日期：2026-08-23

## 背景

项目从数学文档视觉解析起步，但长期范围已经明确扩展到 MathIR、工作流、Skill、推理、
验证与人机协作。仅强调视觉识别的名称无法覆盖这一平台定位，且与多个已有数学产品重名。
M1 刚完成且尚未发布稳定公共 API，此时是完成一次性品牌迁移的最低成本窗口。

## 决策

1. 正式品牌使用 `TensorHub MathCraft`，产品简称使用 `MathCraft`，中文名使用“数理工坊”。
2. 平台子系统固定命名为 `MathCraft Core`、`MathCraft Flow`、`MathCraft Studio` 与
   `MathCraft Skills`；数学中间表示继续使用独立名称 `MathIR`。
3. Python 分发包、导入包与 CLI 统一使用 `mathcraft`；版本化 Schema 使用
   `mathcraft.*` 命名空间。
4. 在稳定版本发布前执行硬迁移，不保留旧包名、旧 CLI 或旧 Schema 的兼容层。
5. GitHub 仓库使用 `TensorHub-ORG/MathCraft`。

## 后果

- 品牌能够同时承载文档解析、数学工作流、协作证明和社区 Skill 生态；
- Core、Flow、Studio、Skills 与 MathIR 的职责在名称层面保持清晰；
- M1 本地工作区需要同步迁移 Schema 与生成物名称；
- 迁移后的首次提交构成新名称下后续公共 API 的起点。

## 未选择的方案

- 不使用仅强调 OCR、扫描或视觉输入的名称，因为 PDF 只是数学信息载体之一。
- 不把 MathIR 改成品牌专属名称，避免削弱它作为稳定交换协议的语义。
- 不保留双 CLI 和双包名，避免在尚无兼容义务时引入长期死逻辑。
