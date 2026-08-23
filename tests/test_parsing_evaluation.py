from pathlib import Path

import pytest

from mathcraft.domain import (
    Block,
    BlockType,
    BoundingBox,
    ContentCandidate,
    CoordinateSpace,
    Document,
    Page,
    SourceDocument,
)
from mathcraft.evaluation import evaluate_parsing
from mathcraft.golden import (
    GoldenBlock,
    GoldenDataset,
    GoldenPage,
    ReviewAspect,
    SuggestionSource,
)

SOURCE_HASH = "a" * 64


def _box(x0: float, y0: float, x1: float, y1: float) -> BoundingBox:
    return BoundingBox(
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        space=CoordinateSpace.NORMALIZED,
    )


def _prediction_block(
    block_id: str,
    block_type: BlockType,
    bbox: BoundingBox,
    content: str,
) -> Block:
    return Block(
        id=block_id,
        type=block_type,
        bbox=bbox,
        candidates=(ContentCandidate(content=content, engine="test"),),
        selected_candidate=0,
    )


def _golden(
    verified_aspects: tuple[ReviewAspect, ...] = (
        ReviewAspect.LAYOUT,
        ReviewAspect.READING_ORDER,
    ),
) -> GoldenDataset:
    blocks = (
        GoldenBlock(
            id="title",
            type=BlockType.TITLE,
            bbox=_box(10, 10, 400, 80),
            source_transcription="高等代数",
            verified_aspects=(ReviewAspect.TRANSCRIPTION,),
        ),
        GoldenBlock(
            id="text",
            type=BlockType.TEXT,
            bbox=_box(10, 100, 900, 200),
            source_transcription="设 A 为矩阵",
            verified_aspects=(ReviewAspect.TRANSCRIPTION,),
        ),
        GoldenBlock(
            id="formula",
            type=BlockType.FORMULA,
            bbox=_box(100, 300, 800, 400),
            latex=r"\det(A - \lambda I)=0",
            verified_aspects=(ReviewAspect.FORMULA,),
            suggested_by=SuggestionSource(
                engine="test",
                engine_version="1.0",
                block_id="p-formula",
            ),
        ),
    )
    return GoldenDataset(
        dataset_id="evaluation-test",
        source=SourceDocument(filename="source.pdf", sha256=SOURCE_HASH),
        source_page_count=1,
        render_dpi=300,
        pages=(
            GoldenPage(
                page_number=1,
                strata=("mixed",),
                rationale="metric contract",
                verified_aspects=verified_aspects,
                blocks=blocks,
                reading_order=("title", "text", "formula"),
            ),
        ),
    )


def _prediction() -> Document:
    blocks = (
        _prediction_block("p-title", BlockType.TITLE, _box(12, 12, 402, 82), "高等代数"),
        _prediction_block(
            "p-formula", BlockType.TEXT, _box(100, 300, 800, 400), r"\det(A-\lambda I)=0"
        ),
        _prediction_block("p-text", BlockType.TEXT, _box(10, 100, 900, 200), "设 A 为矩陈"),
        _prediction_block("false-positive", BlockType.TEXT, _box(10, 700, 300, 800), "噪声"),
    )
    return Document(
        id="prediction",
        source_path=Path("source.pdf"),
        source_sha256=SOURCE_HASH,
        pages=(
            Page(
                number=1,
                width=1000,
                height=1000,
                coordinate_space=CoordinateSpace.NORMALIZED,
                blocks=blocks,
            ),
        ),
    )


def test_parsing_evaluation_reports_layout_content_type_and_order() -> None:
    report = evaluate_parsing(_golden(), _prediction())

    summary = report.summary
    assert summary.matched_blocks == 3
    assert summary.assisted_reference_blocks == 1
    assert summary.layout_precision == pytest.approx(0.75)
    assert summary.layout_recall == 1
    assert summary.type_accuracy == pytest.approx(2 / 3)
    assert summary.reading_order_accuracy == pytest.approx(2 / 3)
    assert summary.text_samples == 2
    assert summary.mean_text_error_rate == pytest.approx(1 / 14)
    assert summary.formula_samples == 1
    assert summary.formula_exact_match_rate == 1


def test_parsing_evaluation_omits_unverified_content_metrics() -> None:
    golden = _golden()
    unverified_pages = tuple(
        page.model_copy(
            update={
                "blocks": tuple(
                    block.model_copy(update={"verified_aspects": ()}) for block in page.blocks
                )
            }
        )
        for page in golden.pages
    )
    report = evaluate_parsing(golden.model_copy(update={"pages": unverified_pages}), _prediction())

    assert report.summary.text_samples == 0
    assert report.summary.mean_text_error_rate is None
    assert report.summary.formula_samples == 0
    assert report.summary.formula_exact_match_rate is None
    assert report.summary.eligible_text_blocks == 2
    assert report.summary.verified_text_blocks == 0
    assert report.summary.eligible_formula_blocks == 1
    assert report.summary.verified_formula_blocks == 0


def test_parsing_evaluation_rejects_unverified_layout() -> None:
    with pytest.raises(ValueError, match="verified layout"):
        evaluate_parsing(_golden(()), _prediction())
