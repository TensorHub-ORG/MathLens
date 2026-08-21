from __future__ import annotations

from pathlib import Path

from mathlens.application.render_document import render_document
from mathlens.golden import GoldenDataset
from mathlens.hashing import sha256_file
from mathlens.ports import PageArtifactStore, PageRenderer


def prepare_golden_dataset(
    selection: GoldenDataset,
    source: Path,
    renderer: PageRenderer,
    store: PageArtifactStore,
) -> GoldenDataset:
    source = source.expanduser().resolve()
    actual_hash = sha256_file(source)
    if actual_hash != selection.source.sha256:
        raise ValueError("source PDF does not match the golden selection SHA-256")

    page_numbers = tuple(page.page_number for page in selection.pages)
    report = render_document(
        renderer=renderer,
        store=store,
        source=source,
        page_numbers=page_numbers,
        dpi=selection.render_dpi,
    )
    artifact_ids = {
        record.manifest.page.page_number: record.manifest.artifact_id for record in report.artifacts
    }
    pages = tuple(
        page.model_copy(update={"image_artifact_id": artifact_ids[page.page_number]})
        for page in selection.pages
    )
    return selection.model_copy(update={"pages": pages})
