from pathlib import Path

import pytest

from mathcraft.application import prepare_parsing_evaluation
from mathcraft.domain import (
    CoordinateSpace,
    Document,
    DocumentParseResult,
    Page,
    SourceDocument,
)
from mathcraft.golden import GoldenDataset, GoldenPage, ReviewAspect

SOURCE_HASH = "a" * 64


def _golden(verified_aspects: tuple[ReviewAspect, ...] = (ReviewAspect.LAYOUT,)) -> GoldenDataset:
    return GoldenDataset(
        dataset_id="evaluation-test",
        source=SourceDocument(filename="source.pdf", sha256=SOURCE_HASH),
        source_page_count=2,
        render_dpi=300,
        pages=(
            GoldenPage(
                page_number=1,
                strata=("mixed",),
                rationale="metric contract",
                verified_aspects=verified_aspects,
            ),
        ),
    )


def _result(page_number: int) -> DocumentParseResult:
    return DocumentParseResult(
        document=Document(
            id=f"prediction-{page_number}",
            source_path=Path("source.pdf"),
            source_sha256=SOURCE_HASH,
            pages=(
                Page(
                    number=page_number,
                    width=1000,
                    height=1000,
                    coordinate_space=CoordinateSpace.NORMALIZED,
                ),
            ),
        ),
        engine="test",
        engine_version="1.0",
        configuration={},
        configuration_hash="b" * 64,
        raw_output_path=Path("raw.json"),
    )


def test_prepare_parsing_evaluation_merges_predictions() -> None:
    golden, prediction = prepare_parsing_evaluation(
        _golden(),
        (_result(2), _result(1)),
        verified_only=True,
    )

    assert [page.page_number for page in golden.pages] == [1]
    assert [page.number for page in prediction.pages] == [1, 2]


def test_prepare_parsing_evaluation_rejects_duplicate_pages() -> None:
    with pytest.raises(ValueError, match="duplicate page numbers"):
        prepare_parsing_evaluation(
            _golden(()),
            (_result(1), _result(1)),
            verified_only=False,
        )


def test_prepare_parsing_evaluation_rejects_predictions_outside_golden_pages() -> None:
    with pytest.raises(ValueError, match="cover no golden pages"):
        prepare_parsing_evaluation(
            _golden(),
            (_result(2),),
            verified_only=False,
        )
