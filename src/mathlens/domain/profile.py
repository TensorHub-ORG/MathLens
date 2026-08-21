from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class PageKind(StrEnum):
    SCANNED = "scanned"
    VECTOR = "vector"
    MIXED = "mixed"
    EMPTY = "empty"


class PageProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int = Field(ge=1)
    width_points: float = Field(gt=0)
    height_points: float = Field(gt=0)
    text_characters: int = Field(ge=0)
    images: int = Field(ge=0)
    drawings: int = Field(ge=0)
    kind: PageKind


class DocumentProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: Path
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_size_bytes: int = Field(ge=0)
    page_count: int = Field(ge=0)
    inspected_pages: tuple[PageProfile, ...]
