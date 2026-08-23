import subprocess
from pathlib import Path
from shutil import copyfile

import pymupdf
import pytest

from mathcraft.adapters.mineru import (
    MinerUCLIAdapter,
    MinerUDevice,
    MinerURuntimeInfo,
    import_content_list_v2,
)
from mathcraft.domain import BlockType, CoordinateSpace, DiagnosticLevel


def _create_source(path: Path) -> None:
    document = pymupdf.open()
    document.new_page()
    document.save(path)
    document.close()


def test_import_content_list_v2_converts_blocks_and_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_source(source)

    result = import_content_list_v2(
        Path("tests/fixtures/mineru_content_list_v2.json"),
        source,
        engine_version="3.0.0",
        start_page=7,
    )

    assert result.document.pages[0].number == 7
    blocks = result.document.pages[0].blocks
    assert [block.type for block in blocks] == [
        BlockType.TITLE,
        BlockType.TEXT,
        BlockType.FORMULA,
    ]
    assert blocks[0].bbox.space is CoordinateSpace.NORMALIZED
    assert blocks[1].candidates[0].content == "设矩阵 A"
    assert blocks[2].candidates[0].content == r"\det(A-\lambda I)=0"
    assert result.diagnostics[0].level is DiagnosticLevel.WARNING
    assert result.diagnostics[0].page_number == 7
    assert result.configuration_hash == result.document.metadata["configuration_hash"]


def test_import_content_list_v2_has_deterministic_document_id(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_source(source)
    content_list = Path("tests/fixtures/mineru_content_list_v2.json")

    first = import_content_list_v2(content_list, source, "3.0.0")
    second = import_content_list_v2(content_list, source, "3.0.0")

    assert first.document.id == second.document.id


def test_mineru_cli_adapter_runs_one_based_page_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output"
    _create_source(source)
    commands: list[list[str]] = []
    parsing_run_options: dict[str, object] = {}

    def fake_run(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        parsing_run_options.update(options)
        mineru_output = output / "source" / "source_content_list_v2.json"
        mineru_output.parent.mkdir(parents=True)
        copyfile("tests/fixtures/mineru_content_list_v2.json", mineru_output)
        return subprocess.CompletedProcess(command, 0, stdout="done\n", stderr="")

    runtime = MinerURuntimeInfo(
        executable="mineru.exe",
        python_executable="python.exe",
        mineru_version="3.0.0",
        torch_version="2.11.0+cu128",
        torch_cuda_version="12.8",
        cuda_available=True,
        cuda_device_count=1,
        cuda_device_name="test GPU",
        cuda_memory_bytes=6 * 1024**3,
        onnxruntime_providers=("CPUExecutionProvider",),
    )
    monkeypatch.setattr(
        "mathcraft.adapters.mineru.cli.resolve_mineru_executable", lambda _: "mineru.exe"
    )
    monkeypatch.setattr(
        "mathcraft.adapters.mineru.cli.probe_mineru_runtime", lambda *_, **__: runtime
    )
    monkeypatch.setattr("mathcraft.adapters.mineru.cli.run_managed_process", fake_run)

    result = MinerUCLIAdapter().parse(source, output, start_page=7, end_page=7)

    assert result.document.pages[0].number == 7
    assert commands[0][commands[0].index("--start") + 1] == "6"
    assert commands[0][commands[0].index("--end") + 1] == "6"
    assert "capture_output" not in parsing_run_options
    assert hasattr(parsing_run_options["stdout"], "write")
    assert "environment" in parsing_run_options
    assert result.configuration == {
        "backend": "pipeline",
        "language": "ch",
        "method": "ocr",
        "service": "local",
        "device": "auto",
        "torch_version": "2.11.0+cu128",
        "torch_cuda_version": "12.8",
        "cuda_device_name": "test GPU",
    }


def test_mineru_cli_adapter_requires_installed_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.pdf"
    _create_source(source)

    def missing(_: str) -> str:
        raise FileNotFoundError("separate runtime")

    monkeypatch.setattr("mathcraft.adapters.mineru.cli.resolve_mineru_executable", missing)

    with pytest.raises(FileNotFoundError, match="separate runtime"):
        MinerUCLIAdapter().parse(source, tmp_path / "output")


def test_mineru_cli_adapter_rejects_unavailable_requested_cuda(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.pdf"
    _create_source(source)
    runtime = MinerURuntimeInfo(
        executable="mineru.exe",
        python_executable="python.exe",
        mineru_version="3.4.5",
        torch_version="2.13.0+cpu",
        torch_cuda_version=None,
        cuda_available=False,
        cuda_device_count=0,
        cuda_device_name=None,
        cuda_memory_bytes=None,
        onnxruntime_providers=("CPUExecutionProvider",),
    )
    monkeypatch.setattr(
        "mathcraft.adapters.mineru.cli.resolve_mineru_executable", lambda _: "mineru.exe"
    )
    monkeypatch.setattr(
        "mathcraft.adapters.mineru.cli.probe_mineru_runtime", lambda *_, **__: runtime
    )

    with pytest.raises(RuntimeError, match="CUDA was requested"):
        MinerUCLIAdapter(device=MinerUDevice.CUDA).parse(source, tmp_path / "output")
