from pathlib import Path

import pymupdf
import pytest

from mathcraft.adapters.filesystem import FileSystemPageArtifactStore
from mathcraft.adapters.pymupdf import PyMuPDFPageRenderer
from mathcraft.application import prepare_golden_dataset
from mathcraft.domain import SourceDocument
from mathcraft.golden import GoldenDataset, GoldenPage
from mathcraft.hashing import sha256_file


def _create_pdf(path: Path) -> None:
    document = pymupdf.open()
    document.new_page()
    document.save(path)
    document.close()


def test_prepare_golden_renders_and_links_selected_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_pdf(source)
    selection = GoldenDataset(
        dataset_id="prepared",
        source=SourceDocument(filename=source.name, sha256=sha256_file(source)),
        source_page_count=1,
        render_dpi=144,
        pages=(GoldenPage(page_number=1, strata=("blank",), rationale="test"),),
    )

    prepared = prepare_golden_dataset(
        selection,
        source,
        PyMuPDFPageRenderer(),
        FileSystemPageArtifactStore(tmp_path / "artifacts"),
    )

    artifact_id = prepared.pages[0].image_artifact_id
    assert artifact_id is not None
    assert (tmp_path / "artifacts" / artifact_id[:2] / artifact_id / "page.png").is_file()


def test_prepare_golden_rejects_wrong_source(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_pdf(source)
    selection = GoldenDataset(
        dataset_id="wrong-source",
        source=SourceDocument(filename=source.name, sha256="0" * 64),
        source_page_count=1,
        render_dpi=144,
        pages=(GoldenPage(page_number=1, strata=("blank",), rationale="test"),),
    )

    with pytest.raises(ValueError, match="SHA-256"):
        prepare_golden_dataset(
            selection,
            source,
            PyMuPDFPageRenderer(),
            FileSystemPageArtifactStore(tmp_path / "artifacts"),
        )
