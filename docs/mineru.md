# MinerU Adapter

MathLens Core 不依赖 MinerU。MinerU 3.x 作为可选的外部运行时，通过 CLI Adapter 或远程
`mineru-api` 接入。Adapter 使用官方 `content_list_v2.json` 作为转换边界，将 0..1000 bbox、
内容类型和阅读顺序转换为 MathIR。

## 独立环境

仓库提供锁定的独立 uv 子项目，不会把 MinerU 安装到 MathLens Core 的 `.venv`：

```powershell
.tools\uv sync --project integrations\mineru
```

当前运行时固定使用 MinerU 3.4.5 的 `pipeline` extra。升级时必须重新运行 golden baseline，
不能用新版本结果覆盖旧报告。

首次真实运行记录见
[MinerU 3.4.5 单页 Smoke Baseline](baselines/mineru-3.4.5-page-7.md)及
[第 7 页 CPU/GPU 对照](baselines/mineru-3.4.5-page-7-gpu.md)。

模型下载、CUDA 或远程服务配置以
[MinerU 官方文档](https://github.com/opendatalab/MinerU/tree/master/docs)为准。运行时目录、模型、
原始输出和用户文档不得提交到 Git。

## 导入已有输出

无需安装 MinerU 即可导入官方 v3 `content_list_v2.json`：

```powershell
mathlens mineru-import result_content_list_v2.json source.pdf --output parse-result.json
```

## 直接运行

当 `mineru` 已在 `PATH` 中时：

```powershell
mathlens mineru-run source.pdf --output-dir workspace\mineru-run \
  --backend pipeline --method ocr --language ch --device cuda \
  --start-page 7 --end-page 7 \
  --executable integrations\mineru\.venv\Scripts\mineru.exe
```

页码在 MathLens CLI 中从 1 开始，Adapter 会转换为 MinerU 的 0 起始 `--start`/`--end`。
输出目录必须为空，避免把旧结果误认为当前运行结果。缺少或非法 bbox 的 MinerU item 不会
被伪造定位；它会被省略并产生结构化诊断。

`--device cuda` 会同时限制可见 GPU、设置 MinerU pipeline 的设备模式，并在运行前检查
CUDA PyTorch；如果不可用会直接报错，不会静默退回 CPU。RTX 4050 6 GB 使用 pipeline，
不选择本地 `vlm-engine` 或 `hybrid-engine`。
