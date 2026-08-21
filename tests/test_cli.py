import json
from pathlib import Path

import pymupdf
from typer.testing import CliRunner

from mathlens.cli import app

runner = CliRunner()


def test_doctor_reports_runtime_and_external_tools() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["mathlens"] == "0.1.0"
    assert report["pymupdf"]
    assert set(report["tools"]) == {"pdfinfo", "pdftoppm", "xelatex", "latexmk"}


def test_inspect_writes_document_profile(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "profile.json"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "MathLens")
    document.save(source)
    document.close()

    result = runner.invoke(app, ["inspect", str(source), "--output", str(output)])

    assert result.exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["page_count"] == 1
    assert report["inspected_pages"][0]["kind"] == "vector"


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
