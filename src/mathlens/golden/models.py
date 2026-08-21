from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mathlens.domain import BlockType, BoundingBox, CoordinateSpace, SourceDocument


class AnnotationStatus(StrEnum):
    SELECTED = "selected"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    ADJUDICATED = "adjudicated"


class GoldenBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    type: BlockType
    bbox: BoundingBox
    source_transcription: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_coordinate_space(self) -> GoldenBlock:
        if self.bbox.space is not CoordinateSpace.NORMALIZED:
            raise ValueError("golden block coordinates must use the normalized 0..1000 space")
        return self


class GoldenPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    strata: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    status: AnnotationStatus = AnnotationStatus.SELECTED
    image_artifact_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    blocks: tuple[GoldenBlock, ...] = ()
    reading_order: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_blocks_and_reading_order(self) -> GoldenPage:
        block_ids = [block.id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("golden block IDs must be unique within a page")
        if len(self.reading_order) != len(set(self.reading_order)):
            raise ValueError("reading order must not contain duplicate block IDs")
        unknown = set(self.reading_order) - set(block_ids)
        if unknown:
            raise ValueError(f"reading order contains unknown block IDs: {sorted(unknown)}")
        if self.status in {AnnotationStatus.REVIEWED, AnnotationStatus.ADJUDICATED} and set(
            self.reading_order
        ) != set(block_ids):
            raise ValueError("reviewed pages must include every block in reading order")
        return self


class GoldenDataset(BaseModel):
    model_config = ConfigDict(frozen=True, serialize_by_alias=True, validate_by_name=True)

    schema_id: Literal["mathlens.golden-dataset.v1"] = Field(
        default="mathlens.golden-dataset.v1",
        alias="schema",
    )
    dataset_id: str = Field(min_length=1)
    source: SourceDocument
    source_page_count: int = Field(ge=1)
    render_dpi: int = Field(ge=72, le=1200)
    pages: tuple[GoldenPage, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_pages(self) -> GoldenDataset:
        page_numbers = [page.page_number for page in self.pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("golden page numbers must be unique")
        invalid = [number for number in page_numbers if number > self.source_page_count]
        if invalid:
            raise ValueError(f"golden pages exceed source page count: {invalid}")
        return self
