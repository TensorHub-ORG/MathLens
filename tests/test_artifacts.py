from pathlib import Path

import pymupdf
import pytest

from mathlens.adapters.filesystem import FileSystemPageArtifactStore
from mathlens.adapters.pymupdf import PyMuPDFPageRenderer
from mathlens.application import render_document
from mathlens.domain import CoordinateSpace


def _create_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=144, height=72)
    page.insert_text((10, 20), "MathLens artifact")
    document.save(path)
    document.close()


def test_render_document_publishes_content_addressed_artifact(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    artifact_root = tmp_path / "artifacts"
    _create_pdf(source)

    report = render_document(
        PyMuPDFPageRenderer(),
        FileSystemPageArtifactStore(artifact_root),
        source,
        page_numbers=(1,),
        dpi=144,
    )

    record = report.artifacts[0]
    manifest = record.manifest
    assert record.directory == artifact_root / manifest.artifact_id[:2] / manifest.artifact_id
    assert record.image_path.is_file()
    assert record.manifest_path.is_file()
    assert manifest.source.filename == "source.pdf"
    assert manifest.page.pixel_width == 288
    assert manifest.page.pixel_height == 144
    assert manifest.page.coordinate_transform.source_space is CoordinateSpace.PDF_POINT
    assert manifest.page.coordinate_transform.target_space is CoordinateSpace.PIXEL
    transform = manifest.page.coordinate_transform
    pixel_point = transform.pdf_point_to_pixel(72, 36)
    assert transform.pixel_to_pdf_point(*pixel_point) == pytest.approx((72, 36))


def test_render_document_reuses_identical_artifact(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    artifact_root = tmp_path / "artifacts"
    _create_pdf(source)
    renderer = PyMuPDFPageRenderer()
    store = FileSystemPageArtifactStore(artifact_root)

    first = render_document(renderer, store, source, page_numbers=(1,), dpi=144)
    first_manifest = first.artifacts[0].manifest
    second = render_document(renderer, store, source, page_numbers=(1,), dpi=144)

    assert second.artifacts[0].manifest == first_manifest
    assert second.artifacts[0].manifest.artifact_id == first_manifest.artifact_id


def test_render_document_detects_corrupted_existing_content(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    artifact_root = tmp_path / "artifacts"
    _create_pdf(source)
    renderer = PyMuPDFPageRenderer()
    store = FileSystemPageArtifactStore(artifact_root)
    first = render_document(renderer, store, source, page_numbers=(1,), dpi=144)
    first.artifacts[0].image_path.write_bytes(b"corrupted")

    with pytest.raises(ValueError, match="content hash mismatch"):
        render_document(renderer, store, source, page_numbers=(1,), dpi=144)


def test_render_document_rejects_duplicate_page_numbers(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_pdf(source)

    with pytest.raises(ValueError, match="must not contain duplicates"):
        render_document(
            PyMuPDFPageRenderer(),
            FileSystemPageArtifactStore(tmp_path / "artifacts"),
            source,
            page_numbers=(1, 1),
        )
