from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mathcraft.golden import ReviewAspect


class ParsingPageEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    verified_aspects: tuple[ReviewAspect, ...]
    reference_blocks: int = Field(ge=0)
    assisted_reference_blocks: int = Field(ge=0)
    predicted_blocks: int = Field(ge=0)
    matched_blocks: int = Field(ge=0)
    layout_precision: float = Field(ge=0, le=1)
    layout_recall: float = Field(ge=0, le=1)
    layout_f1: float = Field(ge=0, le=1)
    mean_iou: float = Field(ge=0, le=1)
    type_accuracy: float | None = Field(default=None, ge=0, le=1)
    reading_order_accuracy: float | None = Field(default=None, ge=0, le=1)
    eligible_text_blocks: int = Field(ge=0)
    verified_text_blocks: int = Field(ge=0)
    text_samples: int = Field(ge=0)
    mean_text_error_rate: float | None = Field(default=None, ge=0)
    eligible_formula_blocks: int = Field(ge=0)
    verified_formula_blocks: int = Field(ge=0)
    formula_samples: int = Field(ge=0)
    formula_exact_match_rate: float | None = Field(default=None, ge=0, le=1)


class ParsingEvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    pages: int = Field(ge=0)
    reference_blocks: int = Field(ge=0)
    assisted_reference_blocks: int = Field(ge=0)
    predicted_blocks: int = Field(ge=0)
    matched_blocks: int = Field(ge=0)
    layout_precision: float = Field(ge=0, le=1)
    layout_recall: float = Field(ge=0, le=1)
    layout_f1: float = Field(ge=0, le=1)
    mean_iou: float = Field(ge=0, le=1)
    type_accuracy: float | None = Field(default=None, ge=0, le=1)
    reading_order_accuracy: float | None = Field(default=None, ge=0, le=1)
    eligible_text_blocks: int = Field(ge=0)
    verified_text_blocks: int = Field(ge=0)
    text_samples: int = Field(ge=0)
    mean_text_error_rate: float | None = Field(default=None, ge=0)
    eligible_formula_blocks: int = Field(ge=0)
    verified_formula_blocks: int = Field(ge=0)
    formula_samples: int = Field(ge=0)
    formula_exact_match_rate: float | None = Field(default=None, ge=0, le=1)


class ParsingPredictionSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_numbers: tuple[int, ...]


class ParsingEvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True, serialize_by_alias=True, validate_by_name=True)

    schema_id: Literal["mathcraft.parsing-evaluation.v2"] = Field(
        default="mathcraft.parsing-evaluation.v2",
        alias="schema",
    )
    dataset_id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prediction_sources: tuple[ParsingPredictionSource, ...] = ()
    iou_threshold: float = Field(gt=0, le=1)
    pages: tuple[ParsingPageEvaluation, ...]
    summary: ParsingEvaluationSummary
