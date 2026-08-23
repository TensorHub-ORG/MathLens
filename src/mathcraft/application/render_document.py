from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from mathcraft.domain.artifacts import (
    PageImageArtifactManifest,
    PageImageMetadata,
    SourceDocument,
)
from mathcraft.hashing import sha256_bytes, sha256_file
from mathcraft.ports import PageArtifactStore, PageRenderer


class PageArtifactRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest: PageImageArtifactManifest
    directory: Path
    image_path: Path
    manifest_path: Path


class RenderDocumentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: Path
    source_sha256: str
    artifacts: tuple[PageArtifactRecord, ...]


def _canonical_hash(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(serialized.encode("utf-8"))


def render_document(
    renderer: PageRenderer,
    store: PageArtifactStore,
    source: Path,
    page_numbers: tuple[int, ...] | None = None,
    dpi: int = 300,
) -> RenderDocumentReport:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if dpi < 72 or dpi > 1200:
        raise ValueError("dpi must be in the range 72..1200")
    if page_numbers is not None and len(page_numbers) != len(set(page_numbers)):
        raise ValueError("page numbers must not contain duplicates")

    source_document = SourceDocument(filename=source.name, sha256=sha256_file(source))
    configuration_hash = _canonical_hash(
        {"alpha": False, "dpi": dpi, "format": "png", "renderer": renderer.engine}
    )
    rendered_pages = renderer.render_pages(source, page_numbers, dpi)
    records = []
    for rendered_page in rendered_pages:
        content_hash = sha256_bytes(rendered_page.png_bytes)
        page_metadata = PageImageMetadata(
            page_number=rendered_page.page_number,
            dpi=rendered_page.dpi,
            pixel_width=rendered_page.pixel_width,
            pixel_height=rendered_page.pixel_height,
            coordinate_transform=rendered_page.coordinate_transform,
        )
        artifact_id = _canonical_hash(
            {
                "configuration_hash": configuration_hash,
                "content_hash": content_hash,
                "engine": renderer.engine,
                "engine_version": renderer.engine_version,
                "page": page_metadata.model_dump(mode="json"),
                "schema": "mathcraft.page-image.v1",
                "source": source_document.model_dump(mode="json"),
                "stage": "page_render",
            }
        )
        manifest = PageImageArtifactManifest(
            artifact_id=artifact_id,
            content_hash=content_hash,
            engine=renderer.engine,
            engine_version=renderer.engine_version,
            configuration_hash=configuration_hash,
            created_at=datetime.now(UTC),
            source=source_document,
            page=page_metadata,
        )
        stored = store.publish(manifest, rendered_page.png_bytes)
        records.append(
            PageArtifactRecord(
                manifest=stored.manifest,
                directory=stored.directory,
                image_path=stored.image_path,
                manifest_path=stored.manifest_path,
            )
        )

    return RenderDocumentReport(
        source_path=source,
        source_sha256=source_document.sha256,
        artifacts=tuple(records),
    )
