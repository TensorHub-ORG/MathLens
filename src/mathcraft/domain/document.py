from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CoordinateSpace(StrEnum):
    PDF_POINT = "pdf_point"
    PIXEL = "pixel"
    NORMALIZED = "normalized"


class BlockType(StrEnum):
    TITLE = "title"
    TEXT = "text"
    FORMULA = "formula"
    FIGURE = "figure"
    TABLE = "table"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"
    PAGE_NUMBER = "page_number"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float
    space: CoordinateSpace

    @model_validator(mode="after")
    def validate_order(self) -> BoundingBox:
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bounding box must have positive width and height")
        if self.space is CoordinateSpace.NORMALIZED:
            values = (self.x0, self.y0, self.x1, self.y1)
            if any(value < 0 or value > 1000 for value in values):
                raise ValueError("normalized coordinates must be in the range 0..1000")
        return self


class ContentCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    engine: str = Field(min_length=1)
    engine_version: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class Block(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    type: BlockType
    bbox: BoundingBox
    candidates: tuple[ContentCandidate, ...] = ()
    selected_candidate: int | None = Field(default=None, ge=0)
    source_crop: Path | None = None

    @model_validator(mode="after")
    def validate_selection(self) -> Block:
        if self.selected_candidate is not None and self.selected_candidate >= len(self.candidates):
            raise ValueError("selected candidate index is out of range")
        return self


class Page(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    coordinate_space: CoordinateSpace
    blocks: tuple[Block, ...] = ()


class Document(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    source_path: Path
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pages: tuple[Page, ...]
    metadata: dict[str, str] = Field(default_factory=dict)
