from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from mathcraft.domain import Block, BlockType, BoundingBox, CoordinateSpace, Document
from mathcraft.evaluation.metrics import normalize_formula, text_error_rate
from mathcraft.evaluation.parsing_models import (
    ParsingEvaluationReport,
    ParsingEvaluationSummary,
    ParsingPageEvaluation,
)
from mathcraft.golden import GoldenBlock, GoldenDataset, GoldenPage, ReviewAspect
from mathcraft.golden.models import TRANSCRIBABLE_BLOCK_TYPES


@dataclass(frozen=True, slots=True)
class _Match:
    reference_index: int
    prediction_index: int
    iou: float


@dataclass(frozen=True, slots=True)
class _PageCounts:
    result: ParsingPageEvaluation
    iou_total: float
    correct_types: int
    reading_pairs: int
    correct_reading_pairs: int
    text_error_total: float
    exact_formulas: int


def _iou(first: BoundingBox, second: BoundingBox) -> float:
    if (
        first.space is not CoordinateSpace.NORMALIZED
        or second.space is not CoordinateSpace.NORMALIZED
    ):
        raise ValueError("parsing evaluation requires normalized 0..1000 coordinates")
    intersection_width = max(0.0, min(first.x1, second.x1) - max(first.x0, second.x0))
    intersection_height = max(0.0, min(first.y1, second.y1) - max(first.y0, second.y0))
    intersection = intersection_width * intersection_height
    first_area = (first.x1 - first.x0) * (first.y1 - first.y0)
    second_area = (second.x1 - second.x0) * (second.y1 - second.y0)
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


def _match_blocks(
    references: tuple[GoldenBlock, ...],
    predictions: tuple[Block, ...],
    threshold: float,
) -> tuple[_Match, ...]:
    candidates = []
    for reference_index, reference in enumerate(references):
        for prediction_index, prediction in enumerate(predictions):
            overlap = _iou(reference.bbox, prediction.bbox)
            if overlap >= threshold:
                candidates.append(_Match(reference_index, prediction_index, overlap))
    candidates.sort(key=lambda match: match.iou, reverse=True)

    used_references: set[int] = set()
    used_predictions: set[int] = set()
    selected = []
    for candidate in candidates:
        if (
            candidate.reference_index in used_references
            or candidate.prediction_index in used_predictions
        ):
            continue
        used_references.add(candidate.reference_index)
        used_predictions.add(candidate.prediction_index)
        selected.append(candidate)
    return tuple(selected)


def _safe_ratio(numerator: int | float, denominator: int) -> float:
    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0
    return numerator / denominator


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _selected_content(block: Block) -> str:
    if block.selected_candidate is None:
        return ""
    return block.candidates[block.selected_candidate].content


def _evaluate_page(
    reference: GoldenPage,
    predictions: tuple[Block, ...],
    threshold: float,
) -> _PageCounts:
    matches = _match_blocks(reference.blocks, predictions, threshold)
    precision = _safe_ratio(len(matches), len(predictions))
    recall = _safe_ratio(len(matches), len(reference.blocks))
    iou_total = sum(match.iou for match in matches)
    correct_types = sum(
        reference.blocks[match.reference_index].type is predictions[match.prediction_index].type
        for match in matches
    )

    reference_order = {block_id: index for index, block_id in enumerate(reference.reading_order)}
    order_pairs = [
        (reference_order[reference.blocks[match.reference_index].id], match.prediction_index)
        for match in matches
        if reference.blocks[match.reference_index].id in reference_order
    ]
    reading_pairs = 0
    correct_reading_pairs = 0
    if ReviewAspect.READING_ORDER in reference.verified_aspects:
        for first, second in combinations(order_pairs, 2):
            reading_pairs += 1
            if (first[0] - second[0]) * (first[1] - second[1]) > 0:
                correct_reading_pairs += 1

    text_errors = []
    formula_matches = []
    for match in matches:
        golden_block = reference.blocks[match.reference_index]
        prediction = _selected_content(predictions[match.prediction_index])
        if golden_block.type is BlockType.FORMULA:
            if (
                ReviewAspect.FORMULA not in golden_block.verified_aspects
                or golden_block.latex is None
            ):
                continue
            formula_matches.append(
                normalize_formula(golden_block.latex) == normalize_formula(prediction)
            )
        else:
            if (
                ReviewAspect.TRANSCRIPTION not in golden_block.verified_aspects
                or golden_block.source_transcription is None
            ):
                continue
            text_errors.append(text_error_rate(golden_block.source_transcription, prediction))

    result = ParsingPageEvaluation(
        page_number=reference.page_number,
        verified_aspects=reference.verified_aspects,
        reference_blocks=len(reference.blocks),
        assisted_reference_blocks=sum(block.suggested_by is not None for block in reference.blocks),
        predicted_blocks=len(predictions),
        matched_blocks=len(matches),
        layout_precision=precision,
        layout_recall=recall,
        layout_f1=_f1(precision, recall),
        mean_iou=_safe_ratio(iou_total, len(matches)),
        type_accuracy=_safe_ratio(correct_types, len(matches)) if matches else None,
        reading_order_accuracy=(
            _safe_ratio(correct_reading_pairs, reading_pairs) if reading_pairs else None
        ),
        eligible_text_blocks=sum(
            block.type in TRANSCRIBABLE_BLOCK_TYPES for block in reference.blocks
        ),
        verified_text_blocks=sum(
            ReviewAspect.TRANSCRIPTION in block.verified_aspects for block in reference.blocks
        ),
        text_samples=len(text_errors),
        mean_text_error_rate=(sum(text_errors) / len(text_errors) if text_errors else None),
        eligible_formula_blocks=sum(block.type is BlockType.FORMULA for block in reference.blocks),
        verified_formula_blocks=sum(
            ReviewAspect.FORMULA in block.verified_aspects for block in reference.blocks
        ),
        formula_samples=len(formula_matches),
        formula_exact_match_rate=(
            sum(formula_matches) / len(formula_matches) if formula_matches else None
        ),
    )
    return _PageCounts(
        result=result,
        iou_total=iou_total,
        correct_types=correct_types,
        reading_pairs=reading_pairs,
        correct_reading_pairs=correct_reading_pairs,
        text_error_total=sum(text_errors),
        exact_formulas=sum(formula_matches),
    )


def evaluate_parsing(
    reference: GoldenDataset,
    prediction: Document,
    iou_threshold: float = 0.5,
) -> ParsingEvaluationReport:
    if iou_threshold <= 0 or iou_threshold > 1:
        raise ValueError("IoU threshold must be in the range (0, 1]")
    incomplete = [
        page.page_number
        for page in reference.pages
        if ReviewAspect.LAYOUT not in page.verified_aspects
    ]
    if incomplete:
        raise ValueError(f"golden pages do not have verified layout: {incomplete}")
    if reference.source.sha256 != prediction.source_sha256:
        raise ValueError("golden dataset and prediction source hashes differ")

    predictions_by_page = {page.number: page.blocks for page in prediction.pages}
    counts = [
        _evaluate_page(page, predictions_by_page.get(page.page_number, ()), iou_threshold)
        for page in reference.pages
    ]
    reference_blocks = sum(item.result.reference_blocks for item in counts)
    predicted_blocks = sum(item.result.predicted_blocks for item in counts)
    matched_blocks = sum(item.result.matched_blocks for item in counts)
    precision = _safe_ratio(matched_blocks, predicted_blocks)
    recall = _safe_ratio(matched_blocks, reference_blocks)
    text_samples = sum(item.result.text_samples for item in counts)
    formula_samples = sum(item.result.formula_samples for item in counts)
    reading_pairs = sum(item.reading_pairs for item in counts)
    summary = ParsingEvaluationSummary(
        pages=len(counts),
        reference_blocks=reference_blocks,
        assisted_reference_blocks=sum(item.result.assisted_reference_blocks for item in counts),
        predicted_blocks=predicted_blocks,
        matched_blocks=matched_blocks,
        layout_precision=precision,
        layout_recall=recall,
        layout_f1=_f1(precision, recall),
        mean_iou=_safe_ratio(sum(item.iou_total for item in counts), matched_blocks),
        type_accuracy=(
            _safe_ratio(sum(item.correct_types for item in counts), matched_blocks)
            if matched_blocks
            else None
        ),
        reading_order_accuracy=(
            _safe_ratio(sum(item.correct_reading_pairs for item in counts), reading_pairs)
            if reading_pairs
            else None
        ),
        eligible_text_blocks=sum(item.result.eligible_text_blocks for item in counts),
        verified_text_blocks=sum(item.result.verified_text_blocks for item in counts),
        text_samples=text_samples,
        mean_text_error_rate=(
            sum(item.text_error_total for item in counts) / text_samples if text_samples else None
        ),
        eligible_formula_blocks=sum(item.result.eligible_formula_blocks for item in counts),
        verified_formula_blocks=sum(item.result.verified_formula_blocks for item in counts),
        formula_samples=formula_samples,
        formula_exact_match_rate=(
            sum(item.exact_formulas for item in counts) / formula_samples
            if formula_samples
            else None
        ),
    )
    return ParsingEvaluationReport(
        dataset_id=reference.dataset_id,
        source_sha256=reference.source.sha256,
        iou_threshold=iou_threshold,
        pages=tuple(item.result for item in counts),
        summary=summary,
    )
