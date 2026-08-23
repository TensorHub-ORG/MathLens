from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvaluationKind(StrEnum):
    TEXT = "text"
    FORMULA = "formula"


class EvaluationSample(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    kind: EvaluationKind
    reference: str
    prediction: str


class EvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_id: str
    kind: EvaluationKind
    exact_match: bool
    edit_distance: int = Field(ge=0)
    error_rate: float = Field(ge=0)


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: EvaluationKind
    samples: int = Field(ge=0)
    exact_match_rate: float = Field(ge=0, le=1)
    mean_error_rate: float = Field(ge=0)


class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: tuple[EvaluationResult, ...]
    summaries: tuple[EvaluationSummary, ...]
