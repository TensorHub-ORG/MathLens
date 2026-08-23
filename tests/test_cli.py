import json
from pathlib import Path

import pymupdf
from typer.testing import CliRunner

from mathcraft.cli import app

runner = CliRunner()


def test_doctor_reports_runtime_and_external_tools() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["mathcraft"] == "0.1.0"
    assert report["pymupdf"]
    assert set(report["tools"]) == {"pdfinfo", "pdftoppm", "xelatex", "latexmk", "mineru"}


def test_inspect_writes_document_profile(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "profile.json"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "MathCraft")
    document.save(source)
    document.close()

    result = runner.invoke(app, ["inspect", str(source), "--output", str(output)])

    assert result.exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["page_count"] == 1
    assert report["inspected_pages"][0]["kind"] == "vector"


def test_render_writes_selected_page_artifact(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifacts"
    document = pymupdf.open()
    document.new_page()
    document.new_page()
    document.save(source)
    document.close()

    result = runner.invoke(
        app,
        ["render", str(source), "--page", "2", "--dpi", "144", "--output-dir", str(output)],
    )

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert len(report["artifacts"]) == 1
    assert report["artifacts"][0]["manifest"]["page"]["page_number"] == 2
    assert Path(report["artifacts"][0]["image_path"]).is_file()


def test_evaluate_writes_report(tmp_path: Path) -> None:
    dataset = tmp_path / "evaluation.jsonl"
    output = tmp_path / "report.json"
    dataset.write_text(
        '{"id":"formula-1","kind":"formula","reference":"A^T A","prediction":"A^7 A"}\n',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["evaluate", str(dataset), "--output", str(output)])

    assert result.exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["results"][0]["exact_match"] is False
    assert report["results"][0]["edit_distance"] == 1


def test_golden_validate_reports_seed_selection() -> None:
    result = runner.invoke(
        app,
        ["golden-validate", "benchmarks/high-algebra-2022-2024/selection.json"],
    )

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["selected_pages"] == 12
    assert report["verified_page_aspect_counts"] == {
        "layout": 0,
        "reading_order": 0,
    }
    assert report["verified_content_blocks"] == {"formula": 0, "transcription": 0}


def test_mineru_import_writes_mathir_result(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "parse-result.json"
    document = pymupdf.open()
    document.new_page()
    document.save(source)
    document.close()

    result = runner.invoke(
        app,
        [
            "mineru-import",
            "tests/fixtures/mineru_content_list_v2.json",
            str(source),
            "--output",
            str(output),
            "--engine-version",
            "3.0.0",
        ],
    )

    assert result.exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["engine"] == "mineru"
    assert report["document"]["pages"][0]["blocks"][2]["type"] == "formula"
