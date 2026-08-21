from pathlib import Path

import pytest
from pydantic import ValidationError

from mathlens.domain import BlockType, BoundingBox, CoordinateSpace, SourceDocument
from mathlens.golden import AnnotationStatus, GoldenBlock, GoldenDataset, GoldenPage


def test_seed_selection_contains_twelve_stratified_pages() -> None:
    selection = GoldenDataset.model_validate_json(
        Path("benchmarks/high-algebra-2022-2024/selection.json").read_text(encoding="utf-8")
    )

    assert len(selection.pages) == 12
    assert selection.pages[0].page_number == 1
    assert selection.pages[-1].page_number == 207
    assert all(page.status is AnnotationStatus.SELECTED for page in selection.pages)


def test_reviewed_page_requires_complete_reading_order() -> None:
    block = GoldenBlock(
        id="b1",
        type=BlockType.TEXT,
        bbox=BoundingBox(
            x0=10,
            y0=10,
            x1=100,
            y1=100,
            space=CoordinateSpace.NORMALIZED,
        ),
    )

    with pytest.raises(ValidationError, match="every block"):
        GoldenPage(
            page_number=1,
            strata=("text",),
            rationale="test",
            status=AnnotationStatus.REVIEWED,
            blocks=(block,),
        )


def test_dataset_rejects_page_past_source_end() -> None:
    with pytest.raises(ValidationError, match="exceed source page count"):
        GoldenDataset(
            dataset_id="invalid",
            source=SourceDocument(filename="source.pdf", sha256="0" * 64),
            source_page_count=1,
            render_dpi=300,
            pages=(GoldenPage(page_number=2, strata=("text",), rationale="test"),),
        )
