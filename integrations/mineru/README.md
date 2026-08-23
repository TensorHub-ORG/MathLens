# MathCraft MinerU Runtime

该目录定义与 MathCraft Core 隔离的 MinerU 运行环境。版本锁定为 MinerU 3.4.5，使用官方
`pipeline` extra，避免把 Torch、Transformers、ONNX Runtime 和模型依赖加入 Core。
运行时另外显式锁定 `six`，因为 MinerU 3.4.5 的 OCR 路径会导入它但上游未声明该依赖。
Windows 运行时锁定官方 PyTorch 2.11 / CUDA 12.8 wheel；RTX 40 系列使用 `pipeline` 后端，
不启用至少需要约 8 GB 显存的本地 VLM/Hybrid engine。

```powershell
.tools\uv sync --project integrations\mineru
```

运行时入口位于：

```text
integrations\mineru\.venv\Scripts\mineru.exe
```

MathCraft Adapter 默认从 `PATH` 查找 `mineru`。也可以先把上述 `Scripts` 目录加入当前会话的
`PATH`。模型来源、缓存位置和 CUDA 配置按 MinerU 官方文档管理，不进入 Git。

安装后先验证 CUDA 可见性：

```powershell
mathcraft mineru-doctor --executable integrations\mineru\.venv\Scripts\mineru.exe
```
