from pathlib import Path

import pytest
from pydantic import ValidationError

from mathlens.domain import BlockType, BoundingBox, CoordinateSpace, SourceDocument
from mathlens.golden import GoldenBlock, GoldenDataset, GoldenPage, ReviewAspect


def test_seed_selection_contains_twelve_stratified_pages() -> None:
    selection = GoldenDataset.model_validate_json(
        Path("benchmarks/high-algebra-2022-2024/selection.json").read_text(encoding="utf-8")
    )

    assert len(selection.pages) == 12
    assert selection.pages[0].page_number == 1
    assert selection.pages[-1].page_number == 207
    assert all(not page.verified_aspects for page in selection.pages)


def test_verified_reading_order_requires_complete_reading_order() -> None:
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
            verified_aspects=(ReviewAspect.LAYOUT, ReviewAspect.READING_ORDER),
            blocks=(block,),
        )


def test_content_verification_requires_verified_layout() -> None:
    with pytest.raises(ValidationError, match="belongs to blocks"):
        GoldenPage(
            page_number=1,
            strata=("text",),
            rationale="test",
            verified_aspects=(ReviewAspect.TRANSCRIPTION,),
        )


def test_v2_page_content_verification_migrates_to_v3_blocks() -> None:
    payload = {
        "schema": "mathlens.golden-dataset.v2",
        "dataset_id": "legacy",
        "source": {"filename": "source.pdf", "sha256": "0" * 64},
        "source_page_count": 1,
        "render_dpi": 300,
        "pages": [
            {
                "page_number": 1,
                "strata": ["formula"],
                "rationale": "migration",
                "verified_aspects": ["layout", "formula"],
                "blocks": [
                    {
                        "id": "f1",
                        "type": "formula",
                        "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10, "space": "normalized"},
                        "latex": "x^2",
                    }
                ],
                "reading_order": ["f1"],
            }
        ],
    }

    dataset = GoldenDataset.model_validate(payload)

    assert dataset.schema_id == "mathlens.golden-dataset.v3"
    assert dataset.pages[0].verified_aspects == (ReviewAspect.LAYOUT,)
    assert dataset.pages[0].blocks[0].verified_aspects == (ReviewAspect.FORMULA,)


def test_dataset_rejects_page_past_source_end() -> None:
    with pytest.raises(ValidationError, match="exceed source page count"):
        GoldenDataset(
            dataset_id="invalid",
            source=SourceDocument(filename="source.pdf", sha256="0" * 64),
            source_page_count=1,
            render_dpi=300,
            pages=(GoldenPage(page_number=2, strata=("text",), rationale="test"),),
        )
