from __future__ import annotations

import shutil
import subprocess
from enum import StrEnum
from pathlib import Path

from mathlens.adapters.mineru.content_list import import_content_list_v2
from mathlens.domain import DocumentParseResult


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


class MinerUCLIAdapter:
    def __init__(
        self,
        executable: str = "mineru",
        backend: MinerUBackend = MinerUBackend.PIPELINE,
        method: MinerUMethod = MinerUMethod.OCR,
        language: str = "ch",
        api_url: str | None = None,
        timeout_seconds: int = 3600,
    ) -> None:
        self._executable = executable
        self._backend = backend
        self._method = method
        self._language = language
        self._api_url = api_url
        self._timeout_seconds = timeout_seconds

    def _resolved_executable(self) -> str:
        resolved = shutil.which(self._executable)
        if resolved is None:
            raise FileNotFoundError(
                f"MinerU executable not found: {self._executable}. "
                "Install it in a separate runtime."
            )
        return resolved

    def _version(self, executable: str) -> str:
        executable_path = Path(executable)
        python_candidates = (
            executable_path.parent / "python.exe",
            executable_path.parent / "python",
        )
        python_executable = next((path for path in python_candidates if path.is_file()), None)
        command = (
            [
                str(python_executable),
                "-c",
                "import importlib.metadata; print(importlib.metadata.version('mineru'))",
            ]
            if python_executable is not None
            else [executable, "--version"]
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise RuntimeError("MinerU version command failed")
        version = (completed.stdout or completed.stderr).strip()
        if not version:
            raise RuntimeError("MinerU version command returned no version")
        return version

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

        executable = self._resolved_executable()
        version = self._version(executable)
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

        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-2000:]
            raise RuntimeError(
                f"MinerU parsing failed with exit code {completed.returncode}: {detail}"
            )

        candidates = tuple(output_directory.rglob("*_content_list_v2.json"))
        if len(candidates) != 1:
            raise RuntimeError(
                f"expected one MinerU content_list_v2 output, found {len(candidates)}"
            )
        return import_content_list_v2(
            candidates[0],
            source,
            engine_version=version,
            start_page=start_page or 1,
            configuration={
                "backend": self._backend.value,
                "language": self._language,
                "method": self._method.value,
                "service": "remote" if self._api_url is not None else "local",
            },
        )
