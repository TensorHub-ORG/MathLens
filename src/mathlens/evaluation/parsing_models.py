from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParsingPageEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    reference_blocks: int = Field(ge=0)
    predicted_blocks: int = Field(ge=0)
    matched_blocks: int = Field(ge=0)
    layout_precision: float = Field(ge=0, le=1)
    layout_recall: float = Field(ge=0, le=1)
    layout_f1: float = Field(ge=0, le=1)
    mean_iou: float = Field(ge=0, le=1)
    type_accuracy: float | None = Field(default=None, ge=0, le=1)
    reading_order_accuracy: float | None = Field(default=None, ge=0, le=1)
    text_samples: int = Field(ge=0)
    mean_text_error_rate: float | None = Field(default=None, ge=0)
    formula_samples: int = Field(ge=0)
    formula_exact_match_rate: float | None = Field(default=None, ge=0, le=1)


class ParsingEvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    pages: int = Field(ge=0)
    reference_blocks: int = Field(ge=0)
    predicted_blocks: int = Field(ge=0)
    matched_blocks: int = Field(ge=0)
    layout_precision: float = Field(ge=0, le=1)
    layout_recall: float = Field(ge=0, le=1)
    layout_f1: float = Field(ge=0, le=1)
    mean_iou: float = Field(ge=0, le=1)
    type_accuracy: float | None = Field(default=None, ge=0, le=1)
    reading_order_accuracy: float | None = Field(default=None, ge=0, le=1)
    text_samples: int = Field(ge=0)
    mean_text_error_rate: float | None = Field(default=None, ge=0)
    formula_samples: int = Field(ge=0)
    formula_exact_match_rate: float | None = Field(default=None, ge=0, le=1)


class ParsingEvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    iou_threshold: float = Field(gt=0, le=1)
    pages: tuple[ParsingPageEvaluation, ...]
    summary: ParsingEvaluationSummary
