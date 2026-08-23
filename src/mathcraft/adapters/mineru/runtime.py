from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_PROBE_PROGRAM = """
import importlib.metadata
import json

import torch

try:
    import onnxruntime
    providers = onnxruntime.get_available_providers()
except ImportError:
    providers = []

cuda_device_count = torch.cuda.device_count()
cuda_available = torch.cuda.is_available() and cuda_device_count > 0
device = torch.cuda.get_device_properties(0) if cuda_available else None
print(json.dumps({
    "mineru_version": importlib.metadata.version("mineru"),
    "torch_version": torch.__version__,
    "torch_cuda_version": torch.version.cuda,
    "cuda_available": cuda_available,
    "cuda_device_count": cuda_device_count,
    "cuda_device_name": device.name if device is not None else None,
    "cuda_memory_bytes": device.total_memory if device is not None else None,
    "onnxruntime_providers": providers,
}))
"""


@dataclass(frozen=True, slots=True)
class MinerURuntimeInfo:
    executable: str
    python_executable: str
    mineru_version: str
    torch_version: str
    torch_cuda_version: str | None
    cuda_available: bool
    cuda_device_count: int
    cuda_device_name: str | None
    cuda_memory_bytes: int | None
    onnxruntime_providers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_mineru_executable(executable: str) -> str:
    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(
            f"MinerU executable not found: {executable}. Install it in a separate runtime."
        )
    return resolved


def _runtime_python(executable: str) -> Path:
    executable_path = Path(executable)
    candidates = (
        executable_path.parent / "python.exe",
        executable_path.parent / "python",
    )
    python_executable = next((path for path in candidates if path.is_file()), None)
    if python_executable is None:
        raise RuntimeError(f"MinerU runtime Python was not found beside {executable}")
    return python_executable


def probe_mineru_runtime(
    executable: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> MinerURuntimeInfo:
    resolved = resolve_mineru_executable(executable)
    python_executable = _runtime_python(resolved)
    completed = subprocess.run(
        [str(python_executable), "-c", _PROBE_PROGRAM],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        env=environment,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-2000:]
        raise RuntimeError(f"MinerU runtime probe failed: {detail}")
    try:
        payload = json.loads(completed.stdout)
        return MinerURuntimeInfo(
            executable=resolved,
            python_executable=str(python_executable),
            mineru_version=str(payload["mineru_version"]),
            torch_version=str(payload["torch_version"]),
            torch_cuda_version=payload["torch_cuda_version"],
            cuda_available=bool(payload["cuda_available"]),
            cuda_device_count=int(payload["cuda_device_count"]),
            cuda_device_name=payload["cuda_device_name"],
            cuda_memory_bytes=payload["cuda_memory_bytes"],
            onnxruntime_providers=tuple(payload["onnxruntime_providers"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("MinerU runtime probe returned invalid JSON") from error
