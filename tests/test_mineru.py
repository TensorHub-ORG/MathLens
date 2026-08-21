import subprocess
from pathlib import Path
from shutil import copyfile

import pymupdf
import pytest

from mathlens.adapters.mineru import MinerUCLIAdapter, import_content_list_v2
from mathlens.domain import BlockType, CoordinateSpace, DiagnosticLevel


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

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, stdout="MinerU 3.0.0\n", stderr="")
        mineru_output = output / "source" / "source_content_list_v2.json"
        mineru_output.parent.mkdir(parents=True)
        copyfile("tests/fixtures/mineru_content_list_v2.json", mineru_output)
        return subprocess.CompletedProcess(command, 0, stdout="done\n", stderr="")

    monkeypatch.setattr("mathlens.adapters.mineru.cli.shutil.which", lambda _: "mineru.exe")
    monkeypatch.setattr("mathlens.adapters.mineru.cli.subprocess.run", fake_run)

    result = MinerUCLIAdapter().parse(source, output, start_page=7, end_page=7)

    assert result.document.pages[0].number == 7
    assert commands[1][commands[1].index("--start") + 1] == "6"
    assert commands[1][commands[1].index("--end") + 1] == "6"
    assert result.configuration == {
        "backend": "pipeline",
        "language": "ch",
        "method": "ocr",
        "service": "local",
    }


def test_mineru_cli_adapter_requires_installed_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.pdf"
    _create_source(source)
    monkeypatch.setattr("mathlens.adapters.mineru.cli.shutil.which", lambda _: None)

    with pytest.raises(FileNotFoundError, match="separate runtime"):
        MinerUCLIAdapter().parse(source, tmp_path / "output")
