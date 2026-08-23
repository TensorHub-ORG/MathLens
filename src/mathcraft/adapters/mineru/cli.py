from __future__ import annotations

import os
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import TextIO, cast

from mathcraft.adapters.mineru.content_list import import_content_list_v2
from mathcraft.adapters.mineru.managed_process import run_managed_process
from mathcraft.adapters.mineru.runtime import probe_mineru_runtime, resolve_mineru_executable
from mathcraft.domain import DocumentParseResult


class MinerUBackend(StrEnum):
    PIPELINE = "pipeline"
    VLM_ENGINE = "vlm-engine"
    HYBRID_ENGINE = "hybrid-engine"
    VLM_HTTP_CLIENT = "vlm-http-client"
    HYBRID_HTTP_CLIENT = "hybrid-http-client"


class MinerUMethod(StrEnum):
    AUTO = "auto"
    TEXT = "txt"
    OCR = "ocr"


class MinerUDevice(StrEnum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


class MinerUCLIAdapter:
    def __init__(
        self,
        executable: str = "mineru",
        backend: MinerUBackend = MinerUBackend.PIPELINE,
        method: MinerUMethod = MinerUMethod.OCR,
        language: str = "ch",
        api_url: str | None = None,
        device: MinerUDevice = MinerUDevice.AUTO,
        gpu_index: int = 0,
        timeout_seconds: int = 3600,
    ) -> None:
        self._executable = executable
        self._backend = backend
        self._method = method
        self._language = language
        self._api_url = api_url
        self._device = device
        self._gpu_index = gpu_index
        self._timeout_seconds = timeout_seconds

    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        if self._device is MinerUDevice.CPU:
            environment["CUDA_VISIBLE_DEVICES"] = ""
            environment["MINERU_DEVICE_MODE"] = "cpu"
        elif self._device is MinerUDevice.CUDA:
            environment["CUDA_VISIBLE_DEVICES"] = str(self._gpu_index)
            environment["MINERU_DEVICE_MODE"] = "cuda"
        return environment

    def parse(
        self,
        source: Path,
        output_directory: Path,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> DocumentParseResult:
        source = source.expanduser().resolve()
        output_directory = output_directory.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if start_page is not None and start_page < 1:
            raise ValueError("start_page must be at least 1")
        if end_page is not None and (start_page is None or end_page < start_page):
            raise ValueError("end_page requires start_page and must not precede it")
        if output_directory.exists() and any(output_directory.iterdir()):
            raise ValueError("MinerU output directory must be empty")
        output_directory.mkdir(parents=True, exist_ok=True)

        if self._gpu_index < 0:
            raise ValueError("gpu_index must not be negative")
        executable = resolve_mineru_executable(self._executable)
        environment = self._environment()
        runtime = probe_mineru_runtime(executable, environment=environment)
        if self._device is MinerUDevice.CUDA and not runtime.cuda_available:
            raise RuntimeError(
                "CUDA was requested but the MinerU runtime cannot access it. "
                f"Installed torch is {runtime.torch_version}."
            )
        command = [
            executable,
            "-p",
            str(source),
            "-o",
            str(output_directory),
            "-b",
            self._backend.value,
            "-m",
            self._method.value,
            "-l",
            self._language,
        ]
        if self._api_url is not None:
            command.extend(("--api-url", self._api_url))
        if start_page is not None:
            command.extend(("--start", str(start_page - 1)))
        if end_page is not None:
            command.extend(("--end", str(end_page - 1)))

        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as log:
            completed = run_managed_process(
                command,
                stdout=cast(TextIO, log),
                timeout=self._timeout_seconds,
                environment=environment,
            )
            if completed.returncode != 0:
                log.seek(0)
                detail = log.read().strip()[-2000:]
                raise RuntimeError(
                    f"MinerU parsing failed with exit code {completed.returncode}: {detail}"
                )

        candidates = tuple(output_directory.rglob("*_content_list_v2.json"))
        if len(candidates) != 1:
            raise RuntimeError(
                f"expected one MinerU content_list_v2 output, found {len(candidates)}"
            )
        configuration = {
            "backend": self._backend.value,
            "language": self._language,
            "method": self._method.value,
            "service": "remote" if self._api_url is not None else "local",
            "device": self._device.value,
            "torch_version": runtime.torch_version,
        }
        if self._device is MinerUDevice.CUDA:
            configuration["gpu_index"] = str(self._gpu_index)
        if runtime.torch_cuda_version is not None:
            configuration["torch_cuda_version"] = runtime.torch_cuda_version
        if runtime.cuda_device_name is not None:
            configuration["cuda_device_name"] = runtime.cuda_device_name
        return import_content_list_v2(
            candidates[0],
            source,
            engine_version=runtime.mineru_version,
            start_page=start_page or 1,
            configuration=configuration,
        )
