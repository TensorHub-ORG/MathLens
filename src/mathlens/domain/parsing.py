from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from mathlens.domain.document import Document


class DiagnosticLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ParseDiagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: DiagnosticLevel
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    item_index: int | None = Field(default=None, ge=0)


class DocumentParseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    document: Document
    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    configuration: dict[str, str]
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_output_path: Path
    diagnostics: tuple[ParseDiagnostic, ...] = ()
