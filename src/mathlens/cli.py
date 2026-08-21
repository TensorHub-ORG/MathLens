from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Annotated

import pymupdf
import typer
from pydantic import ValidationError

from mathlens import __version__
from mathlens.adapters.filesystem import FileSystemPageArtifactStore
from mathlens.adapters.pymupdf import PyMuPDFPageRenderer, PyMuPDFProfiler
from mathlens.application import render_document
from mathlens.evaluation import EvaluationSample, evaluate_samples

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


@app.command()
def version() -> None:
    """Print the installed MathLens version."""
    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Check the local runtime and document-processing tools."""
    tools = ("pdfinfo", "pdftoppm", "xelatex", "latexmk")
    report = {
        "mathlens": __version__,
        "python": sys.version.split()[0],
        "pymupdf": pymupdf.VersionBind,
        "tools": {name: shutil.which(name) for name in tools},
    }
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


@app.command("inspect")
def inspect_document(
    source: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    max_pages: Annotated[int | None, typer.Option(min=1)] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Profile a PDF without applying OCR or modifying the source."""
    profile = PyMuPDFProfiler().inspect(source, max_pages=max_pages)
    payload = profile.model_dump_json(indent=2)
    if output is None:
        typer.echo(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload + "\n", encoding="utf-8")
    typer.echo(str(output.resolve()))


@app.command("render")
def render_pages(
    source: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("artifacts"),
    page: Annotated[list[int] | None, typer.Option("--page", min=1)] = None,
    dpi: Annotated[int, typer.Option(min=72, max=1200)] = 300,
) -> None:
    """Render selected PDF pages into immutable, content-addressed artifacts."""
    try:
        report = render_document(
            renderer=PyMuPDFPageRenderer(),
            store=FileSystemPageArtifactStore(output_dir),
            source=source,
            page_numbers=tuple(page) if page else None,
            dpi=dpi,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(report.model_dump_json(indent=2))


@app.command()
def evaluate(
    dataset: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Evaluate a JSONL golden dataset containing text or formula samples."""
    samples = []
    try:
        with dataset.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    samples.append(EvaluationSample.model_validate_json(line))
                except ValidationError as error:
                    raise typer.BadParameter(f"invalid row {line_number}: {error}") from error
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"invalid JSON: {error}") from error

    report = evaluate_samples(samples)
    payload = report.model_dump_json(indent=2)
    if output is None:
        typer.echo(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload + "\n", encoding="utf-8")
    typer.echo(str(output.resolve()))
