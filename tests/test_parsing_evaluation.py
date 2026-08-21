from pathlib import Path

import pytest

from mathlens.domain import (
    Block,
    BlockType,
    BoundingBox,
    ContentCandidate,
    CoordinateSpace,
    Document,
    Page,
    SourceDocument,
)
from mathlens.evaluation import evaluate_parsing
from mathlens.golden import AnnotationStatus, GoldenBlock, GoldenDataset, GoldenPage

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


def _golden(status: AnnotationStatus = AnnotationStatus.REVIEWED) -> GoldenDataset:
    blocks = (
        GoldenBlock(
            id="title",
            type=BlockType.TITLE,
            bbox=_box(10, 10, 400, 80),
            source_transcription="高等代数",
        ),
        GoldenBlock(
            id="text",
            type=BlockType.TEXT,
            bbox=_box(10, 100, 900, 200),
            source_transcription="设 A 为矩阵",
        ),
        GoldenBlock(
            id="formula",
            type=BlockType.FORMULA,
            bbox=_box(100, 300, 800, 400),
            source_transcription=r"\det(A - \lambda I)=0",
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
                status=status,
                blocks=blocks,
                reading_order=("title", "text", "formula")
                if status is not AnnotationStatus.DRAFT
                else (),
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
    assert summary.layout_precision == pytest.approx(0.75)
    assert summary.layout_recall == 1
    assert summary.type_accuracy == pytest.approx(2 / 3)
    assert summary.reading_order_accuracy == pytest.approx(2 / 3)
    assert summary.text_samples == 2
    assert summary.mean_text_error_rate == pytest.approx(1 / 14)
    assert summary.formula_exact_match_rate == 1


def test_parsing_evaluation_rejects_unreviewed_golden_page() -> None:
    with pytest.raises(ValueError, match="not reviewed"):
        evaluate_parsing(_golden(AnnotationStatus.DRAFT), _prediction())
