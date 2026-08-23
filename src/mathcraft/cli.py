from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Annotated

import pymupdf
import typer
from pydantic import ValidationError

from mathcraft import __version__
from mathcraft.adapters.filesystem import FileSystemPageArtifactStore
from mathcraft.adapters.mineru import (
    MinerUBackend,
    MinerUCLIAdapter,
    MinerUDevice,
    MinerUMethod,
    import_content_list_v2,
    probe_mineru_runtime,
)
from mathcraft.adapters.pymupdf import PyMuPDFPageRenderer, PyMuPDFProfiler
from mathcraft.application import (
    prepare_golden_dataset,
    prepare_parsing_evaluation,
    render_document,
)
from mathcraft.domain import DocumentParseResult
from mathcraft.evaluation import (
    EvaluationSample,
    ParsingPredictionSource,
    evaluate_parsing,
    evaluate_samples,
)
from mathcraft.golden import GoldenDataset, ReviewAspect
from mathcraft.studio import GoldenWorkspace
from mathcraft.studio.server import serve_studio

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


@app.command()
def version() -> None:
    """Print the installed MathCraft version."""
    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Check the local runtime and document-processing tools."""
    tools = ("pdfinfo", "pdftoppm", "xelatex", "latexmk", "mineru")
    report = {
        "mathcraft": __version__,
        "python": sys.version.split()[0],
        "pymupdf": pymupdf.VersionBind,
        "tools": {name: shutil.which(name) for name in tools},
    }
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


@app.command("mineru-doctor")
def doctor_mineru(
    executable: Annotated[str, typer.Option()] = "mineru",
) -> None:
    """Inspect the isolated MinerU runtime and its CUDA visibility."""
    try:
        runtime = probe_mineru_runtime(executable)
    except (FileNotFoundError, RuntimeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(runtime.as_dict(), ensure_ascii=False, indent=2))


@app.command("golden-prepare")
def prepare_golden(
    selection: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    source: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    artifact_dir: Annotated[Path, typer.Option("--artifact-dir")],
    output: Annotated[Path, typer.Option("--output", "-o")],
) -> None:
    """Render selected pages and create a local annotation-ready golden template."""
    try:
        golden_selection = GoldenDataset.model_validate_json(selection.read_text(encoding="utf-8"))
        prepared = prepare_golden_dataset(
            selection=golden_selection,
            source=source,
            renderer=PyMuPDFPageRenderer(),
            store=FileSystemPageArtifactStore(artifact_dir),
        )
    except (ValidationError, json.JSONDecodeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(prepared.model_dump_json(indent=2) + "\n", encoding="utf-8")
    typer.echo(str(output.resolve()))


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


@app.command("golden-validate")
def validate_golden_dataset(
    dataset: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
) -> None:
    """Validate a golden dataset or selection manifest."""
    try:
        golden = GoldenDataset.model_validate_json(dataset.read_text(encoding="utf-8"))
    except (ValidationError, json.JSONDecodeError) as error:
        raise typer.BadParameter(f"invalid golden dataset: {error}") from error
    report = {
        "dataset_id": golden.dataset_id,
        "source_sha256": golden.source.sha256,
        "selected_pages": len(golden.pages),
        "page_numbers": [page.page_number for page in golden.pages],
        "verified_page_aspect_counts": {
            aspect.value: sum(aspect in page.verified_aspects for page in golden.pages)
            for aspect in (ReviewAspect.LAYOUT, ReviewAspect.READING_ORDER)
        },
        "verified_content_blocks": {
            aspect.value: sum(
                aspect in block.verified_aspects for page in golden.pages for block in page.blocks
            )
            for aspect in (ReviewAspect.TRANSCRIPTION, ReviewAspect.FORMULA)
        },
    }
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


@app.command("evaluate-parsing")
def evaluate_parsing_output(
    reference: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    prediction: Annotated[list[Path], typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    iou_threshold: Annotated[float, typer.Option(min=0.01, max=1.0)] = 0.5,
    verified_only: Annotated[bool, typer.Option("--verified-only")] = False,
) -> None:
    """Evaluate one or more MathIR parser outputs against a golden dataset."""
    try:
        golden = GoldenDataset.model_validate_json(reference.read_text(encoding="utf-8"))
        parsed = tuple(
            DocumentParseResult.model_validate_json(path.read_text(encoding="utf-8"))
            for path in prediction
        )
        selected_golden, merged_prediction = prepare_parsing_evaluation(
            golden,
            parsed,
            verified_only=verified_only,
        )
        report = evaluate_parsing(
            selected_golden,
            merged_prediction,
            iou_threshold=iou_threshold,
        )
        report = report.model_copy(
            update={
                "prediction_sources": tuple(
                    ParsingPredictionSource(
                        engine=result.engine,
                        engine_version=result.engine_version,
                        configuration_hash=result.configuration_hash,
                        page_numbers=tuple(page.number for page in result.document.pages),
                    )
                    for result in parsed
                )
            }
        )
    except (ValidationError, json.JSONDecodeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    payload = report.model_dump_json(indent=2)
    if output is None:
        typer.echo(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload + "\n", encoding="utf-8")
    typer.echo(str(output.resolve()))


@app.command("mineru-import")
def import_mineru_output(
    content_list: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    source: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    output: Annotated[Path, typer.Option("--output", "-o")],
    engine_version: Annotated[str, typer.Option()] = "unknown",
    start_page: Annotated[int, typer.Option(min=1)] = 1,
) -> None:
    """Convert MinerU v3 content_list_v2 JSON into MathIR."""
    try:
        result = import_content_list_v2(
            content_list,
            source,
            engine_version=engine_version,
            start_page=start_page,
        )
    except (ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    typer.echo(str(output.resolve()))


@app.command("mineru-run")
def run_mineru(
    source: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")],
    backend: Annotated[MinerUBackend, typer.Option()] = MinerUBackend.PIPELINE,
    method: Annotated[MinerUMethod, typer.Option()] = MinerUMethod.OCR,
    language: Annotated[str, typer.Option()] = "ch",
    start_page: Annotated[int | None, typer.Option(min=1)] = None,
    end_page: Annotated[int | None, typer.Option(min=1)] = None,
    api_url: Annotated[str | None, typer.Option()] = None,
    executable: Annotated[str, typer.Option()] = "mineru",
    device: Annotated[MinerUDevice, typer.Option()] = MinerUDevice.AUTO,
    gpu_index: Annotated[int, typer.Option(min=0)] = 0,
) -> None:
    """Run an optional MinerU 3.x CLI runtime and convert its v2 content list."""
    adapter = MinerUCLIAdapter(
        executable=executable,
        backend=backend,
        method=method,
        language=language,
        api_url=api_url,
        device=device,
        gpu_index=gpu_index,
    )
    try:
        result = adapter.parse(
            source,
            output_dir,
            start_page=start_page,
            end_page=end_page,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    result_path = output_dir.resolve() / "mathcraft-parse-result.json"
    result_path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    typer.echo(str(result_path))


@app.command("golden-studio")
def run_golden_studio(
    dataset: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)],
    artifact_dir: Annotated[
        Path, typer.Option("--artifact-dir", exists=True, file_okay=False, dir_okay=True)
    ],
    prediction: Annotated[
        list[Path] | None,
        typer.Option("--prediction", exists=True, file_okay=True, dir_okay=False),
    ] = None,
    studio_dir: Annotated[Path, typer.Option("--studio-dir")] = Path("studio/dist"),
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option(min=1, max=65535)] = 8765,
) -> None:
    """Run the local Golden Annotation Workbench."""
    if not (studio_dir / "index.html").is_file():
        raise typer.BadParameter(f"studio frontend is not built: {studio_dir}")
    try:
        workspace = GoldenWorkspace(
            dataset,
            artifact_dir,
            tuple(prediction or ()),
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"MathCraft Golden Workbench: http://{host}:{port}")
    serve_studio(workspace, studio_dir, host, port)
